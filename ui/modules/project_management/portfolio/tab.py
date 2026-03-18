from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.platform.notifications.domain_events import domain_events
from core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError
from core.platform.common.models import DependencyType, PortfolioIntakeStatus
from core.platform.auth import UserSessionContext
from core.modules.project_management.services.portfolio import PortfolioService
from core.modules.project_management.services.project import ProjectService
from ui.modules.project_management.portfolio.scenario_dialog import PortfolioScenarioDialog
from ui.modules.project_management.portfolio.scoring_template_dialog import (
    PortfolioScoringTemplateDialog,
)
from ui.platform.shared.async_job import JobUiConfig, start_async_job
from ui.platform.shared.guards import apply_permission_hint, has_permission
from ui.platform.shared.styles.style_utils import style_table
from ui.platform.shared.styles.ui_config import UIConfig as CFG
from ui.platform.shared.worker_services import service_uses_in_memory_sqlite, worker_service_scope


class PortfolioTab(QWidget):
    def __init__(
        self,
        *,
        portfolio_service: PortfolioService,
        project_service: ProjectService,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._portfolio_service = portfolio_service
        self._project_service = project_service
        self._user_session = user_session
        self._can_manage = has_permission(self._user_session, "portfolio.manage")
        self._available_projects = []
        self._available_intake_items = []
        self._available_templates = []
        self._available_dependency_rows = []
        self._current_heatmap_rows = []
        self._pending_local_portfolio_refresh = ""
        self._reload_inflight = False
        self._reload_pending = False
        self._setup_ui()
        self.reload_data()
        domain_events.project_changed.connect(self._on_domain_change)
        domain_events.portfolio_changed.connect(self._on_domain_change)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_MD)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        title = QLabel("Portfolio Planning")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        subtitle = QLabel(
            "Capture proposed work, score it, and compare saved portfolio scenarios side by side."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        split = QHBoxLayout()
        split.setSpacing(CFG.SPACING_MD)
        root.addLayout(split, 1)

        intake_box = QGroupBox("Intake")
        intake_layout = QVBoxLayout(intake_box)
        self.active_template_label = QLabel("Active template: Balanced PMO")
        self.active_template_label.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.active_template_label.setWordWrap(True)
        intake_layout.addWidget(self.active_template_label)

        template_row = QHBoxLayout()
        template_row.addWidget(QLabel("Scoring template"))
        self.intake_template = QComboBox()
        template_row.addWidget(self.intake_template, 1)
        self.btn_new_template = QPushButton("New Template")
        self.btn_activate_template = QPushButton("Set Active")
        for button in (self.btn_new_template, self.btn_activate_template):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            template_row.addWidget(button)
        intake_layout.addLayout(template_row)

        intake_form = QGridLayout()
        intake_form.setHorizontalSpacing(CFG.SPACING_MD)
        intake_form.setVerticalSpacing(CFG.SPACING_SM)
        self.intake_title = QLineEdit()
        self.intake_sponsor = QLineEdit()
        self.intake_budget = QDoubleSpinBox()
        self.intake_budget.setMaximum(1_000_000_000)
        self.intake_capacity = QDoubleSpinBox()
        self.intake_capacity.setMaximum(100000)
        self.intake_status = QComboBox()
        for status in PortfolioIntakeStatus:
            self.intake_status.addItem(status.value.title(), userData=status)
        self.score_strategic = self._score_spin()
        self.score_value = self._score_spin()
        self.score_urgency = self._score_spin()
        self.score_risk = self._score_spin()
        intake_form.addWidget(QLabel("Title"), 0, 0)
        intake_form.addWidget(self.intake_title, 0, 1)
        intake_form.addWidget(QLabel("Sponsor"), 0, 2)
        intake_form.addWidget(self.intake_sponsor, 0, 3)
        intake_form.addWidget(QLabel("Budget"), 1, 0)
        intake_form.addWidget(self.intake_budget, 1, 1)
        intake_form.addWidget(QLabel("Capacity %"), 1, 2)
        intake_form.addWidget(self.intake_capacity, 1, 3)
        intake_form.addWidget(QLabel("Status"), 2, 0)
        intake_form.addWidget(self.intake_status, 2, 1)
        intake_form.addWidget(QLabel("Strategic"), 3, 0)
        intake_form.addWidget(self.score_strategic, 3, 1)
        intake_form.addWidget(QLabel("Value"), 3, 2)
        intake_form.addWidget(self.score_value, 3, 3)
        intake_form.addWidget(QLabel("Urgency"), 4, 0)
        intake_form.addWidget(self.score_urgency, 4, 1)
        intake_form.addWidget(QLabel("Risk"), 4, 2)
        intake_form.addWidget(self.score_risk, 4, 3)
        intake_layout.addLayout(intake_form)
        intake_button_row = QHBoxLayout()
        self.btn_add_intake = QPushButton("Add Intake Item")
        self.btn_reload = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        for button in (self.btn_add_intake, self.btn_reload):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            intake_button_row.addWidget(button)
        intake_button_row.addStretch()
        intake_layout.addLayout(intake_button_row)
        self.intake_table = QTableWidget(0, 7)
        self.intake_table.setHorizontalHeaderLabels(
            ["Title", "Sponsor", "Template", "Status", "Budget", "Capacity %", "Score"]
        )
        self.intake_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.intake_table.setSelectionMode(QTableWidget.SingleSelection)
        self.intake_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.intake_table.horizontalHeader().setStretchLastSection(True)
        style_table(self.intake_table)
        intake_layout.addWidget(self.intake_table, 1)
        split.addWidget(intake_box, 1)

        scenario_box = QGroupBox("Scenarios")
        scenario_layout = QVBoxLayout(scenario_box)
        scenario_button_row = QHBoxLayout()
        self.btn_save_scenario = QPushButton("New Scenario")
        for button in (self.btn_save_scenario,):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            scenario_button_row.addWidget(button)
        scenario_button_row.addStretch()
        scenario_layout.addLayout(scenario_button_row)

        self.scenario_options_label = QLabel("Scenario options: 0 project(s), 0 intake item(s).")
        self.scenario_options_label.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.scenario_options_label.setWordWrap(True)
        scenario_layout.addWidget(self.scenario_options_label)

        self.scenario_tabs = QTabWidget()
        self.scenario_tabs.setDocumentMode(True)
        scenario_layout.addWidget(self.scenario_tabs, 1)

        self.scenario_table = QTableWidget(0, 5)
        self.scenario_table.setHorizontalHeaderLabels(
            ["Name", "Budget Limit", "Capacity Limit %", "Projects", "Intake Items"]
        )
        self.scenario_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.scenario_table.setSelectionMode(QTableWidget.SingleSelection)
        self.scenario_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.scenario_table.horizontalHeader().setStretchLastSection(True)
        style_table(self.scenario_table)
        saved_page = QWidget()
        saved_layout = QVBoxLayout(saved_page)
        saved_layout.setContentsMargins(0, 0, 0, 0)
        saved_layout.setSpacing(CFG.SPACING_SM)
        saved_hint = QLabel("Saved scenarios stay here for review, selection, and quick evaluation.")
        saved_hint.setStyleSheet(CFG.INFO_TEXT_STYLE)
        saved_hint.setWordWrap(True)
        saved_layout.addWidget(saved_hint)
        saved_actions = QHBoxLayout()
        self.btn_evaluate = QPushButton("Evaluate Selected")
        self.btn_evaluate.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_evaluate.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        saved_actions.addStretch()
        saved_actions.addWidget(self.btn_evaluate)
        saved_layout.addLayout(saved_actions)
        saved_layout.addWidget(self.scenario_table, 1)

        self.scenario_summary = QLabel("Select or create a scenario to evaluate.")
        self.scenario_summary.setWordWrap(True)
        self.scenario_summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        saved_layout.addWidget(self.scenario_summary)
        self.scenario_tabs.addTab(saved_page, "Saved Scenarios")

        self.comparison_table = QTableWidget(0, 4)
        self.comparison_table.setHorizontalHeaderLabels(["Metric", "Selected", "Comparison", "Delta"])
        self.comparison_table.setSelectionMode(QTableWidget.NoSelection)
        self.comparison_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.comparison_table.horizontalHeader().setStretchLastSection(True)
        style_table(self.comparison_table)
        compare_page = QWidget()
        compare_layout = QVBoxLayout(compare_page)
        compare_layout.setContentsMargins(0, 0, 0, 0)
        compare_layout.setSpacing(CFG.SPACING_SM)
        compare_hint = QLabel("Choose any two saved scenarios to compare budget, capacity, and selection changes.")
        compare_hint.setStyleSheet(CFG.INFO_TEXT_STYLE)
        compare_hint.setWordWrap(True)
        compare_layout.addWidget(compare_hint)
        compare_form = QGridLayout()
        compare_form.setHorizontalSpacing(CFG.SPACING_MD)
        compare_form.setVerticalSpacing(CFG.SPACING_SM)
        self.base_compare_scenario = QComboBox()
        self.compare_scenario = QComboBox()
        compare_form.addWidget(QLabel("Base scenario"), 0, 0)
        compare_form.addWidget(self.base_compare_scenario, 0, 1)
        compare_form.addWidget(QLabel("Compare against"), 1, 0)
        compare_form.addWidget(self.compare_scenario, 1, 1)
        compare_layout.addLayout(compare_form)
        compare_actions = QHBoxLayout()
        self.btn_compare = QPushButton("Compare Scenarios")
        self.btn_compare.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_compare.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        compare_actions.addStretch()
        compare_actions.addWidget(self.btn_compare)
        compare_layout.addLayout(compare_actions)
        compare_layout.addWidget(self.comparison_table, 1)

        self.comparison_summary = QLabel("Select two saved scenarios to compare.")
        self.comparison_summary.setWordWrap(True)
        self.comparison_summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        compare_layout.addWidget(self.comparison_summary)
        self.scenario_tabs.addTab(compare_page, "Compare")

        self.heatmap_table = QTableWidget(0, 7)
        self.heatmap_table.setHorizontalHeaderLabels(
            ["Project", "Status", "Late Tasks", "Critical", "Peak Util %", "Cost Variance", "Pressure"]
        )
        self.heatmap_table.setSelectionMode(QTableWidget.NoSelection)
        self.heatmap_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.heatmap_table.horizontalHeader().setStretchLastSection(True)
        style_table(self.heatmap_table)
        heatmap_page = QWidget()
        heatmap_layout = QVBoxLayout(heatmap_page)
        heatmap_layout.setContentsMargins(0, 0, 0, 0)
        heatmap_layout.setSpacing(CFG.SPACING_SM)
        heatmap_hint = QLabel(
            "Cross-project delivery pressure across the accessible PM portfolio."
        )
        heatmap_hint.setStyleSheet(CFG.INFO_TEXT_STYLE)
        heatmap_hint.setWordWrap(True)
        heatmap_layout.addWidget(heatmap_hint)
        heatmap_layout.addWidget(self.heatmap_table, 1)
        self.scenario_tabs.addTab(heatmap_page, "Heatmap")

        self.dependency_table = QTableWidget(0, 7)
        self.dependency_table.setHorizontalHeaderLabels(
            ["Predecessor", "Pred Status", "Type", "Successor", "Succ Status", "Pressure", "Summary"]
        )
        self.dependency_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.dependency_table.setSelectionMode(QTableWidget.SingleSelection)
        self.dependency_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.dependency_table.horizontalHeader().setStretchLastSection(True)
        style_table(self.dependency_table)
        dependency_page = QWidget()
        dependency_layout = QVBoxLayout(dependency_page)
        dependency_layout.setContentsMargins(0, 0, 0, 0)
        dependency_layout.setSpacing(CFG.SPACING_SM)
        dependency_hint = QLabel(
            "Portfolio-level links between projects for shared delivery sequencing, without turning on cross-project task links."
        )
        dependency_hint.setStyleSheet(CFG.INFO_TEXT_STYLE)
        dependency_hint.setWordWrap(True)
        dependency_layout.addWidget(dependency_hint)
        dependency_form = QGridLayout()
        dependency_form.setHorizontalSpacing(CFG.SPACING_MD)
        dependency_form.setVerticalSpacing(CFG.SPACING_SM)
        self.dependency_predecessor = QComboBox()
        self.dependency_successor = QComboBox()
        self.dependency_type = QComboBox()
        for dependency_type in DependencyType:
            self.dependency_type.addItem(self._dependency_type_label(dependency_type), userData=dependency_type)
        self.dependency_summary = QLineEdit()
        dependency_form.addWidget(QLabel("Predecessor project"), 0, 0)
        dependency_form.addWidget(self.dependency_predecessor, 0, 1)
        dependency_form.addWidget(QLabel("Successor project"), 0, 2)
        dependency_form.addWidget(self.dependency_successor, 0, 3)
        dependency_form.addWidget(QLabel("Type"), 1, 0)
        dependency_form.addWidget(self.dependency_type, 1, 1)
        dependency_form.addWidget(QLabel("Summary"), 1, 2)
        dependency_form.addWidget(self.dependency_summary, 1, 3)
        dependency_layout.addLayout(dependency_form)
        dependency_actions = QHBoxLayout()
        self.dependency_label = QLabel("Cross-project dependencies: 0")
        self.dependency_label.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.dependency_label.setWordWrap(True)
        dependency_actions.addWidget(self.dependency_label, 1)
        self.btn_add_dependency = QPushButton("Add Dependency")
        self.btn_remove_dependency = QPushButton("Remove Selected")
        for button in (self.btn_add_dependency, self.btn_remove_dependency):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            dependency_actions.addWidget(button)
        dependency_layout.addLayout(dependency_actions)
        dependency_layout.addWidget(self.dependency_table, 1)
        self.scenario_tabs.addTab(dependency_page, "Dependencies")

        self.audit_table = QTableWidget(0, 5)
        self.audit_table.setHorizontalHeaderLabels(["When", "Project", "Actor", "Action", "Summary"])
        self.audit_table.setSelectionMode(QTableWidget.NoSelection)
        self.audit_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.audit_table.horizontalHeader().setStretchLastSection(True)
        style_table(self.audit_table)
        audit_page = QWidget()
        audit_layout = QVBoxLayout(audit_page)
        audit_layout.setContentsMargins(0, 0, 0, 0)
        audit_layout.setSpacing(CFG.SPACING_SM)
        audit_hint = QLabel(
            "Recent PM delivery actions across accessible projects, focused on changes worth executive review."
        )
        audit_hint.setStyleSheet(CFG.INFO_TEXT_STYLE)
        audit_hint.setWordWrap(True)
        audit_layout.addWidget(audit_hint)
        audit_layout.addWidget(self.audit_table, 1)
        self.scenario_tabs.addTab(audit_page, "Recent Actions")

        split.addWidget(scenario_box, 1)

        self.btn_reload.clicked.connect(self.reload_data)
        self.btn_add_intake.clicked.connect(self._create_intake_item)
        self.btn_new_template.clicked.connect(self._create_scoring_template)
        self.btn_activate_template.clicked.connect(self._activate_selected_template)
        self.btn_save_scenario.clicked.connect(self._save_scenario)
        self.btn_evaluate.clicked.connect(self._evaluate_selected_scenario)
        self.btn_compare.clicked.connect(self._compare_selected_scenario)
        self.btn_add_dependency.clicked.connect(self._create_project_dependency)
        self.btn_remove_dependency.clicked.connect(self._remove_selected_dependency)
        self.scenario_table.itemSelectionChanged.connect(self._load_selected_scenario)
        self.dependency_table.itemSelectionChanged.connect(self._update_dependency_buttons)
        self.base_compare_scenario.currentIndexChanged.connect(self._on_compare_base_changed)
        apply_permission_hint(
            self.btn_add_intake,
            allowed=self._can_manage,
            missing_permission="portfolio.manage",
        )
        apply_permission_hint(
            self.btn_save_scenario,
            allowed=self._can_manage,
            missing_permission="portfolio.manage",
        )
        apply_permission_hint(
            self.btn_new_template,
            allowed=self._can_manage,
            missing_permission="portfolio.manage",
        )
        apply_permission_hint(
            self.btn_activate_template,
            allowed=self._can_manage,
            missing_permission="portfolio.manage",
        )
        apply_permission_hint(
            self.btn_add_dependency,
            allowed=self._can_manage,
            missing_permission="portfolio.manage",
        )
        apply_permission_hint(
            self.btn_remove_dependency,
            allowed=self._can_manage,
            missing_permission="portfolio.manage",
        )

    def reload_data(self) -> None:
        selected_scenario_id = self._selected_scenario_id()
        selected_dependency_id = self._selected_dependency_id()
        preferred_base_compare_id = str(self.base_compare_scenario.currentData() or "")
        preferred_compare_id = str(self.compare_scenario.currentData() or "")
        preferred_template_id = str(self.intake_template.currentData() or "")
        if self._reload_inflight:
            self._reload_pending = True
            return

        show_progress = self.sender() is self.btn_reload if hasattr(self, "btn_reload") else False

        def _set_busy(busy: bool) -> None:
            self._reload_inflight = busy
            self.btn_reload.setEnabled(not busy)
            if busy:
                for button in (
                    self.btn_add_intake,
                    self.btn_new_template,
                    self.btn_activate_template,
                    self.btn_save_scenario,
                    self.btn_evaluate,
                    self.btn_compare,
                    self.btn_add_dependency,
                    self.btn_remove_dependency,
                ):
                    button.setEnabled(False)
            else:
                self.btn_add_intake.setEnabled(self._can_manage)
                self.btn_new_template.setEnabled(self._can_manage)
                self.btn_activate_template.setEnabled(self._can_manage)
                self.btn_save_scenario.setEnabled(self._can_manage)
                self.btn_evaluate.setEnabled(True)
                self.btn_compare.setEnabled(True)
                self.btn_add_dependency.setEnabled(self._can_manage)
                self._update_dependency_buttons()
            if not busy and self._reload_pending:
                self._reload_pending = False
                self.reload_data()

        def _load_snapshot(portfolio_service, project_service):
            heatmap_rows = portfolio_service.list_portfolio_heatmap()
            return {
                "intake_items": portfolio_service.list_intake_items(),
                "scoring_templates": portfolio_service.list_scoring_templates(),
                "scenarios": portfolio_service.list_scenarios(),
                "heatmap_rows": heatmap_rows,
                "dependency_rows": portfolio_service.list_project_dependencies(
                    heatmap_rows=heatmap_rows
                ),
                "recent_actions": portfolio_service.list_recent_pm_actions(limit=24),
                "projects": project_service.list_projects(),
            }

        def _work(token, progress):
            token.raise_if_cancelled()
            progress(None, "Loading portfolio data...")
            with worker_service_scope(self._user_session) as services:
                token.raise_if_cancelled()
                return _load_snapshot(services["portfolio_service"], services["project_service"])

        def _on_success(snapshot) -> None:
            intake_items = snapshot["intake_items"]
            scoring_templates = snapshot["scoring_templates"]
            scenarios = snapshot["scenarios"]
            heatmap_rows = snapshot["heatmap_rows"]
            dependency_rows = snapshot["dependency_rows"]
            recent_actions = snapshot["recent_actions"]
            projects = snapshot["projects"]

            self._available_projects = list(projects)
            self._available_intake_items = list(intake_items)
            self._available_templates = list(scoring_templates)
            self._current_heatmap_rows = list(heatmap_rows)
            self._available_dependency_rows = list(dependency_rows)
            self._reload_template_selector(scoring_templates, preferred_template_id=preferred_template_id)
            self._reload_dependency_project_selectors(projects)
            self._update_active_template_label(scoring_templates)
            self.scenario_options_label.setText(
                f"Scenario options: {len(projects)} project(s), {len(intake_items)} intake item(s)."
            )

            self.intake_table.setRowCount(len(intake_items))
            for row_idx, intake_item in enumerate(intake_items):
                values = [
                    intake_item.title,
                    intake_item.sponsor_name,
                    intake_item.scoring_template_name or "-",
                    intake_item.status.value,
                    f"{float(intake_item.requested_budget or 0.0):.2f}",
                    f"{float(intake_item.requested_capacity_percent or 0.0):.1f}",
                    str(intake_item.composite_score),
                ]
                for col, value in enumerate(values):
                    cell = QTableWidgetItem(value)
                    if col == 0:
                        cell.setData(Qt.UserRole, intake_item.id)
                    self.intake_table.setItem(row_idx, col, cell)

            self.scenario_table.setRowCount(len(scenarios))
            for row_idx, scenario in enumerate(scenarios):
                values = [
                    scenario.name,
                    "-" if scenario.budget_limit is None else f"{float(scenario.budget_limit):.2f}",
                    "-" if scenario.capacity_limit_percent is None else f"{float(scenario.capacity_limit_percent):.1f}",
                    str(len(scenario.project_ids)),
                    str(len(scenario.intake_item_ids)),
                ]
                for col, value in enumerate(values):
                    cell = QTableWidgetItem(value)
                    if col == 0:
                        cell.setData(Qt.UserRole, scenario.id)
                    self.scenario_table.setItem(row_idx, col, cell)
            self._restore_scenario_selection(scenarios, selected_scenario_id)
            self._reload_compare_selectors(
                scenarios,
                preferred_base_id=self._selected_scenario_id() or preferred_base_compare_id,
                preferred_compare_id=preferred_compare_id,
            )
            self._populate_heatmap_table(heatmap_rows)
            self._populate_dependency_table(dependency_rows)
            self._restore_dependency_selection(dependency_rows, selected_dependency_id)
            self._update_dependency_buttons()
            self._populate_audit_table(recent_actions)
            if self.base_compare_scenario.count() <= 1 or self.compare_scenario.count() <= 1:
                self._clear_comparison()

        def _on_error(message: str) -> None:
            if message:
                QMessageBox.warning(self, "Portfolio", message)

        if service_uses_in_memory_sqlite(self._portfolio_service):
            _set_busy(True)
            try:
                snapshot = _load_snapshot(self._portfolio_service, self._project_service)
                _on_success(snapshot)
            except Exception as exc:
                _on_error(str(exc))
            finally:
                _set_busy(False)
            return

        start_async_job(
            parent=self,
            ui=JobUiConfig(
                title="Portfolio",
                label="Refreshing portfolio planning workspace...",
                allow_retry=True,
                show_progress=show_progress,
            ),
            work=_work,
            on_success=_on_success,
            on_error=_on_error,
            on_cancel=lambda: None,
            set_busy=_set_busy,
        )

    def _create_intake_item(self) -> None:
        if not self._can_manage:
            QMessageBox.information(self, "Portfolio", "Creating intake items requires portfolio.manage.")
            return
        try:
            self._portfolio_service.create_intake_item(
                title=self.intake_title.text(),
                sponsor_name=self.intake_sponsor.text(),
                requested_budget=float(self.intake_budget.value()),
                requested_capacity_percent=float(self.intake_capacity.value()),
                strategic_score=int(self.score_strategic.value()),
                value_score=int(self.score_value.value()),
                urgency_score=int(self.score_urgency.value()),
                risk_score=int(self.score_risk.value()),
                scoring_template_id=str(self.intake_template.currentData() or ""),
                status=self.intake_status.currentData(),
            )
        except (BusinessRuleError, ValidationError, NotFoundError) as exc:
            QMessageBox.warning(self, "Portfolio", str(exc))
            return
        self.intake_title.clear()
        self.intake_sponsor.clear()
        self.intake_budget.setValue(0.0)
        self.intake_capacity.setValue(0.0)
        self.reload_data()

    def _create_scoring_template(self) -> None:
        if not self._can_manage:
            QMessageBox.information(self, "Portfolio", "Managing scoring templates requires portfolio.manage.")
            return
        dialog = PortfolioScoringTemplateDialog(self)
        if dialog.exec() != PortfolioScoringTemplateDialog.Accepted:
            return
        try:
            self._portfolio_service.create_scoring_template(
                name=dialog.template_name,
                summary=dialog.template_summary,
                strategic_weight=int(dialog.strategic_weight.value()),
                value_weight=int(dialog.value_weight.value()),
                urgency_weight=int(dialog.urgency_weight.value()),
                risk_weight=int(dialog.risk_weight.value()),
                activate=dialog.activate_check.isChecked(),
            )
        except (BusinessRuleError, ValidationError, NotFoundError) as exc:
            QMessageBox.warning(self, "Portfolio", str(exc))
            return
        self.reload_data()

    def _activate_selected_template(self) -> None:
        if not self._can_manage:
            QMessageBox.information(self, "Portfolio", "Managing scoring templates requires portfolio.manage.")
            return
        template_id = str(self.intake_template.currentData() or "")
        if not template_id:
            QMessageBox.information(self, "Portfolio", "Select a scoring template first.")
            return
        try:
            self._portfolio_service.activate_scoring_template(template_id)
        except (BusinessRuleError, ValidationError, NotFoundError) as exc:
            QMessageBox.warning(self, "Portfolio", str(exc))
            return
        self.reload_data()

    def _save_scenario(self) -> None:
        if not self._can_manage:
            QMessageBox.information(self, "Portfolio", "Saving scenarios requires portfolio.manage.")
            return
        dialog = PortfolioScenarioDialog(
            projects=self._available_projects,
            intake_items=self._available_intake_items,
            parent=self,
        )
        if dialog.exec() != PortfolioScenarioDialog.Accepted:
            return
        try:
            self._portfolio_service.create_scenario(
                name=dialog.scenario_name,
                budget_limit=dialog.budget_limit,
                capacity_limit_percent=dialog.capacity_limit_percent,
                project_ids=dialog.project_ids,
                intake_item_ids=dialog.intake_item_ids,
            )
        except (BusinessRuleError, ValidationError, NotFoundError) as exc:
            QMessageBox.warning(self, "Portfolio", str(exc))
            return
        self.reload_data()

    def _evaluate_selected_scenario(self) -> None:
        scenario_id = self._selected_scenario_id()
        if not scenario_id:
            QMessageBox.information(self, "Portfolio", "Select a scenario to evaluate.")
            return
        try:
            result = self._portfolio_service.evaluate_scenario(scenario_id)
        except (BusinessRuleError, ValidationError, NotFoundError) as exc:
            QMessageBox.warning(self, "Portfolio", str(exc))
            return
        self.scenario_summary.setText(result.summary)

    def _compare_selected_scenario(self) -> None:
        scenario_id = str(self.base_compare_scenario.currentData() or "")
        compare_id = str(self.compare_scenario.currentData() or "")
        if not scenario_id:
            QMessageBox.information(self, "Portfolio", "Select a base scenario first.")
            return
        if not compare_id:
            QMessageBox.information(self, "Portfolio", "Select a comparison scenario.")
            return
        try:
            comparison = self._portfolio_service.compare_scenarios(scenario_id, compare_id)
        except (BusinessRuleError, ValidationError, NotFoundError) as exc:
            QMessageBox.warning(self, "Portfolio", str(exc))
            return
        self._render_comparison(comparison)

    def _load_selected_scenario(self) -> None:
        scenario_id = self._selected_scenario_id()
        if not scenario_id:
            self.scenario_summary.setText("Select a saved scenario to evaluate.")
            return
        scenarios = self._portfolio_service.list_scenarios()
        self._reload_compare_selectors(
            scenarios,
            preferred_base_id=scenario_id,
            preferred_compare_id=str(self.compare_scenario.currentData() or ""),
        )
        scenarios_by_id = {scenario.id: scenario for scenario in scenarios}
        scenario = scenarios_by_id.get(scenario_id)
        if scenario is None:
            self.scenario_summary.setText("Select a saved scenario to evaluate.")
            return
        budget_limit = "-" if scenario.budget_limit is None else f"{float(scenario.budget_limit):.2f}"
        capacity_limit = (
            "-"
            if scenario.capacity_limit_percent is None
            else f"{float(scenario.capacity_limit_percent):.1f}%"
        )
        self.scenario_summary.setText(
            f"Selected {scenario.name}: budget limit {budget_limit}; capacity limit {capacity_limit}; "
            f"{len(scenario.project_ids)} project(s); {len(scenario.intake_item_ids)} intake item(s)."
        )

    def _selected_scenario_id(self) -> str:
        row = self.scenario_table.currentRow()
        if row < 0:
            return ""
        item = self.scenario_table.item(row, 0)
        return str(item.data(Qt.UserRole) or "") if item is not None else ""

    def _on_domain_change(self, payload: str) -> None:
        if self._pending_local_portfolio_refresh == "dependencies":
            self._pending_local_portfolio_refresh = ""
            self._refresh_dependency_views(preferred_dependency_id=payload)
            return
        self.reload_data()

    def _create_project_dependency(self) -> None:
        if not self._can_manage:
            QMessageBox.information(self, "Portfolio", "Managing dependencies requires portfolio.manage.")
            return
        predecessor_project_id = str(self.dependency_predecessor.currentData() or "")
        successor_project_id = str(self.dependency_successor.currentData() or "")
        if not predecessor_project_id or not successor_project_id:
            QMessageBox.information(self, "Portfolio", "Select two projects first.")
            return
        try:
            self._pending_local_portfolio_refresh = "dependencies"
            self._portfolio_service.create_project_dependency(
                predecessor_project_id=predecessor_project_id,
                successor_project_id=successor_project_id,
                dependency_type=self.dependency_type.currentData(),
                summary=self.dependency_summary.text(),
            )
        except (BusinessRuleError, ValidationError, NotFoundError) as exc:
            self._pending_local_portfolio_refresh = ""
            QMessageBox.warning(self, "Portfolio", str(exc))
            return
        self.dependency_summary.clear()
        if self._pending_local_portfolio_refresh == "dependencies":
            self._pending_local_portfolio_refresh = ""
            self._refresh_dependency_views()

    def _remove_selected_dependency(self) -> None:
        if not self._can_manage:
            QMessageBox.information(self, "Portfolio", "Managing dependencies requires portfolio.manage.")
            return
        dependency_id = self._selected_dependency_id()
        if not dependency_id:
            QMessageBox.information(self, "Portfolio", "Select a dependency to remove.")
            return
        try:
            self._pending_local_portfolio_refresh = "dependencies"
            self._portfolio_service.remove_project_dependency(dependency_id)
        except (BusinessRuleError, ValidationError, NotFoundError) as exc:
            self._pending_local_portfolio_refresh = ""
            QMessageBox.warning(self, "Portfolio", str(exc))
            return
        if self._pending_local_portfolio_refresh == "dependencies":
            self._pending_local_portfolio_refresh = ""
            self._refresh_dependency_views()

    def _reload_compare_selectors(
        self,
        scenarios,
        *,
        preferred_base_id: str = "",
        preferred_compare_id: str = "",
    ) -> None:
        self.base_compare_scenario.blockSignals(True)
        try:
            self.base_compare_scenario.clear()
            self.base_compare_scenario.addItem("Select scenario", userData="")
            selected_index = 0
            for scenario in scenarios:
                self.base_compare_scenario.addItem(scenario.name, userData=scenario.id)
                if scenario.id == preferred_base_id:
                    selected_index = self.base_compare_scenario.count() - 1
            self.base_compare_scenario.setCurrentIndex(selected_index)
        finally:
            self.base_compare_scenario.blockSignals(False)
        self._reload_compare_candidates(
            scenarios,
            selected_base_id=str(self.base_compare_scenario.currentData() or ""),
            preferred_compare_id=preferred_compare_id,
        )

    def _reload_compare_candidates(
        self,
        scenarios,
        *,
        selected_base_id: str,
        preferred_compare_id: str = "",
    ) -> None:
        self.compare_scenario.blockSignals(True)
        try:
            self.compare_scenario.clear()
            self.compare_scenario.addItem("Select scenario", userData="")
            selected_index = 0
            for scenario in scenarios:
                if scenario.id == selected_base_id:
                    continue
                self.compare_scenario.addItem(scenario.name, userData=scenario.id)
                if scenario.id == preferred_compare_id:
                    selected_index = self.compare_scenario.count() - 1
            self.compare_scenario.setCurrentIndex(selected_index)
        finally:
            self.compare_scenario.blockSignals(False)

    def _reload_template_selector(self, templates, *, preferred_template_id: str = "") -> None:
        self.intake_template.blockSignals(True)
        try:
            self.intake_template.clear()
            selected_index = 0
            active_template_id = ""
            for template in templates:
                label = (
                    f"{template.name} "
                    f"(Sx{template.strategic_weight}, Vx{template.value_weight}, "
                    f"Ux{template.urgency_weight}, Rx{template.risk_weight})"
                )
                if template.is_active:
                    label += " [Active]"
                    active_template_id = template.id
                self.intake_template.addItem(label, userData=template.id)
            for idx in range(self.intake_template.count()):
                current_id = str(self.intake_template.itemData(idx) or "")
                if current_id == preferred_template_id or (not preferred_template_id and current_id == active_template_id):
                    selected_index = idx
                    break
            if self.intake_template.count() > 0:
                self.intake_template.setCurrentIndex(selected_index)
        finally:
            self.intake_template.blockSignals(False)

    def _reload_dependency_project_selectors(self, projects) -> None:
        current_predecessor = str(self.dependency_predecessor.currentData() or "")
        current_successor = str(self.dependency_successor.currentData() or "")
        for combo, preferred_id in (
            (self.dependency_predecessor, current_predecessor),
            (self.dependency_successor, current_successor),
        ):
            combo.blockSignals(True)
            try:
                combo.clear()
                combo.addItem("Select project", userData="")
                selected_index = 0
                for project in projects:
                    combo.addItem(project.name, userData=project.id)
                    if project.id == preferred_id:
                        selected_index = combo.count() - 1
                combo.setCurrentIndex(selected_index)
            finally:
                combo.blockSignals(False)

    def _update_active_template_label(self, templates) -> None:
        active_template = next((template for template in templates if template.is_active), None)
        if active_template is None:
            self.active_template_label.setText("Active template: -")
            return
        self.active_template_label.setText(
            f"Active template: {active_template.name}. {active_template.weight_summary}"
        )

    def _restore_scenario_selection(self, scenarios, scenario_id: str) -> None:
        if not scenario_id:
            return
        for row_idx, scenario in enumerate(scenarios):
            if scenario.id != scenario_id:
                continue
            self.scenario_table.selectRow(row_idx)
            return

    def _render_comparison(self, comparison) -> None:
        rows = [
            (
                "Projects",
                str(comparison.base_evaluation.selected_projects),
                str(comparison.candidate_evaluation.selected_projects),
                f"{comparison.selected_projects_delta:+d}",
            ),
            (
                "Intake Items",
                str(comparison.base_evaluation.selected_intake_items),
                str(comparison.candidate_evaluation.selected_intake_items),
                f"{comparison.selected_intake_items_delta:+d}",
            ),
            (
                "Total Budget",
                f"{comparison.base_evaluation.total_budget:.2f}",
                f"{comparison.candidate_evaluation.total_budget:.2f}",
                f"{comparison.budget_delta:+.2f}",
            ),
            (
                "Capacity %",
                f"{comparison.base_evaluation.total_capacity_percent:.1f}",
                f"{comparison.candidate_evaluation.total_capacity_percent:.1f}",
                f"{comparison.capacity_delta_percent:+.1f}",
            ),
            (
                "Intake Score",
                str(comparison.base_evaluation.intake_composite_score),
                str(comparison.candidate_evaluation.intake_composite_score),
                f"{comparison.intake_score_delta:+d}",
            ),
            (
                "Status",
                self._evaluation_state_label(comparison.base_evaluation),
                self._evaluation_state_label(comparison.candidate_evaluation),
                "-",
            ),
        ]
        self.comparison_table.setRowCount(len(rows))
        for row_idx, values in enumerate(rows):
            for col, value in enumerate(values):
                self.comparison_table.setItem(row_idx, col, QTableWidgetItem(value))
        self.comparison_summary.setText(comparison.summary)

    def _clear_comparison(self) -> None:
        self.comparison_table.setRowCount(0)
        self.comparison_summary.setText("Select two saved scenarios to compare.")

    def _populate_heatmap_table(self, rows) -> None:
        self.heatmap_table.setRowCount(len(rows))
        for row_idx, item in enumerate(rows):
            values = [
                item.project_name,
                item.project_status,
                str(item.late_tasks),
                str(item.critical_tasks),
                f"{float(item.peak_utilization_percent):.1f}",
                f"{float(item.cost_variance):+.2f}",
                item.pressure_label,
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if item.pressure_label == "Hot":
                    font = cell.font()
                    font.setBold(True)
                    cell.setFont(font)
                self.heatmap_table.setItem(row_idx, col, cell)

    def _populate_dependency_table(self, rows) -> None:
        self.dependency_label.setText(f"Cross-project dependencies: {len(rows)}")
        self.dependency_table.setRowCount(len(rows))
        for row_idx, item in enumerate(rows):
            values = [
                item.predecessor_project_name,
                item.predecessor_project_status,
                self._dependency_type_label(item.dependency_type),
                item.successor_project_name,
                item.successor_project_status,
                item.pressure_label,
                item.summary or "-",
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if col == 0:
                    cell.setData(Qt.UserRole, item.dependency_id)
                if item.pressure_label == "Hot":
                    font = cell.font()
                    font.setBold(True)
                    cell.setFont(font)
                self.dependency_table.setItem(row_idx, col, cell)

    def _populate_audit_table(self, rows) -> None:
        self.audit_table.setRowCount(len(rows))
        for row_idx, item in enumerate(rows):
            values = [
                item.occurred_at.strftime("%Y-%m-%d %H:%M"),
                item.project_name,
                item.actor_username,
                item.action_label,
                item.summary,
            ]
            for col, value in enumerate(values):
                self.audit_table.setItem(row_idx, col, QTableWidgetItem(value))

    def _refresh_dependency_views(self, *, preferred_dependency_id: str = "") -> None:
        selected_dependency_id = preferred_dependency_id or self._selected_dependency_id()
        try:
            dependency_rows = self._portfolio_service.list_project_dependencies(
                heatmap_rows=self._current_heatmap_rows or None
            )
            recent_actions = self._portfolio_service.list_recent_pm_actions(limit=24)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Portfolio", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Portfolio", f"Failed to refresh dependencies:\n{exc}")
            return
        self._available_dependency_rows = list(dependency_rows)
        self._populate_dependency_table(dependency_rows)
        self._restore_dependency_selection(dependency_rows, selected_dependency_id)
        self._update_dependency_buttons()
        self._populate_audit_table(recent_actions)

    def _on_compare_base_changed(self) -> None:
        scenarios = self._portfolio_service.list_scenarios()
        self._reload_compare_candidates(
            scenarios,
            selected_base_id=str(self.base_compare_scenario.currentData() or ""),
            preferred_compare_id=str(self.compare_scenario.currentData() or ""),
        )
        self._clear_comparison()

    def _selected_dependency_id(self) -> str:
        row = self.dependency_table.currentRow()
        if row < 0:
            return ""
        item = self.dependency_table.item(row, 0)
        return str(item.data(Qt.UserRole) or "") if item is not None else ""

    def _restore_dependency_selection(self, rows, dependency_id: str) -> None:
        if not dependency_id:
            return
        for row_idx, item in enumerate(rows):
            if item.dependency_id != dependency_id:
                continue
            self.dependency_table.selectRow(row_idx)
            return

    def _update_dependency_buttons(self) -> None:
        self.btn_remove_dependency.setEnabled(self._can_manage and bool(self._selected_dependency_id()))

    @staticmethod
    def _score_spin() -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(1, 5)
        spin.setValue(3)
        return spin

    @staticmethod
    def _dependency_type_label(dependency_type: DependencyType) -> str:
        mapping = {
            DependencyType.FINISH_TO_START: "Finish -> Start",
            DependencyType.FINISH_TO_FINISH: "Finish -> Finish",
            DependencyType.START_TO_START: "Start -> Start",
            DependencyType.START_TO_FINISH: "Start -> Finish",
        }
        return mapping.get(dependency_type, dependency_type.value)

    @staticmethod
    def _evaluation_state_label(result) -> str:
        if result.over_budget and result.over_capacity:
            return "Over budget and capacity"
        if result.over_budget:
            return "Over budget"
        if result.over_capacity:
            return "Over capacity"
        return "Within limits"


__all__ = ["PortfolioTab"]
