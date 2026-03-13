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
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.platform.notifications.domain_events import domain_events
from core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError
from core.platform.common.models import PortfolioIntakeStatus
from core.platform.auth import UserSessionContext
from core.modules.project_management.services.portfolio import PortfolioService
from core.modules.project_management.services.project import ProjectService
from ui.platform.shared.guards import apply_permission_hint, has_permission
from ui.platform.shared.styles.style_utils import style_table
from ui.platform.shared.styles.ui_config import UIConfig as CFG


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
            "Capture proposed work, score it, and evaluate simple portfolio scenarios against budget and capacity."
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
        self.intake_table = QTableWidget(0, 6)
        self.intake_table.setHorizontalHeaderLabels(["Title", "Sponsor", "Status", "Budget", "Capacity %", "Score"])
        self.intake_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.intake_table.setSelectionMode(QTableWidget.SingleSelection)
        self.intake_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.intake_table.horizontalHeader().setStretchLastSection(True)
        style_table(self.intake_table)
        intake_layout.addWidget(self.intake_table, 1)
        split.addWidget(intake_box, 1)

        scenario_box = QGroupBox("Scenarios")
        scenario_layout = QVBoxLayout(scenario_box)
        scenario_form = QGridLayout()
        scenario_form.setHorizontalSpacing(CFG.SPACING_MD)
        scenario_form.setVerticalSpacing(CFG.SPACING_SM)
        self.scenario_name = QLineEdit()
        self.scenario_budget = QDoubleSpinBox()
        self.scenario_budget.setMaximum(1_000_000_000)
        self.scenario_capacity = QDoubleSpinBox()
        self.scenario_capacity.setMaximum(100000)
        scenario_form.addWidget(QLabel("Name"), 0, 0)
        scenario_form.addWidget(self.scenario_name, 0, 1)
        scenario_form.addWidget(QLabel("Budget Limit"), 1, 0)
        scenario_form.addWidget(self.scenario_budget, 1, 1)
        scenario_form.addWidget(QLabel("Capacity Limit %"), 1, 2)
        scenario_form.addWidget(self.scenario_capacity, 1, 3)
        scenario_layout.addLayout(scenario_form)

        selection_row = QHBoxLayout()
        self.project_list = QListWidget()
        self.project_list.setSelectionMode(QListWidget.MultiSelection)
        self.intake_list = QListWidget()
        self.intake_list.setSelectionMode(QListWidget.MultiSelection)
        selection_row.addWidget(self.project_list, 1)
        selection_row.addWidget(self.intake_list, 1)
        scenario_layout.addLayout(selection_row, 1)

        scenario_button_row = QHBoxLayout()
        self.btn_save_scenario = QPushButton("Save Scenario")
        self.btn_evaluate = QPushButton("Evaluate Selected")
        for button in (self.btn_save_scenario, self.btn_evaluate):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            scenario_button_row.addWidget(button)
        scenario_button_row.addStretch()
        scenario_layout.addLayout(scenario_button_row)

        self.scenario_table = QTableWidget(0, 5)
        self.scenario_table.setHorizontalHeaderLabels(
            ["Name", "Budget Limit", "Capacity Limit %", "Projects", "Intake Items"]
        )
        self.scenario_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.scenario_table.setSelectionMode(QTableWidget.SingleSelection)
        self.scenario_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.scenario_table.horizontalHeader().setStretchLastSection(True)
        style_table(self.scenario_table)
        scenario_layout.addWidget(self.scenario_table, 1)

        self.scenario_summary = QLabel("Select or create a scenario to evaluate.")
        self.scenario_summary.setWordWrap(True)
        self.scenario_summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        scenario_layout.addWidget(self.scenario_summary)
        split.addWidget(scenario_box, 1)

        self.btn_reload.clicked.connect(self.reload_data)
        self.btn_add_intake.clicked.connect(self._create_intake_item)
        self.btn_save_scenario.clicked.connect(self._save_scenario)
        self.btn_evaluate.clicked.connect(self._evaluate_selected_scenario)
        self.scenario_table.itemSelectionChanged.connect(self._load_selected_scenario)
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

    def reload_data(self) -> None:
        try:
            intake_items = self._portfolio_service.list_intake_items()
            scenarios = self._portfolio_service.list_scenarios()
            projects = self._project_service.list_projects()
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Portfolio", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Portfolio", f"Failed to load portfolio data:\n{exc}")
            return

        self.project_list.clear()
        for project in projects:
            item = QListWidgetItem(project.name)
            item.setData(Qt.UserRole, project.id)
            self.project_list.addItem(item)

        self.intake_list.clear()
        for intake_item in intake_items:
            item = QListWidgetItem(
                f"{intake_item.title} ({intake_item.composite_score})"
            )
            item.setData(Qt.UserRole, intake_item.id)
            self.intake_list.addItem(item)

        self.intake_table.setRowCount(len(intake_items))
        for row_idx, intake_item in enumerate(intake_items):
            values = [
                intake_item.title,
                intake_item.sponsor_name,
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

    def _save_scenario(self) -> None:
        if not self._can_manage:
            QMessageBox.information(self, "Portfolio", "Saving scenarios requires portfolio.manage.")
            return
        project_ids = [str(item.data(Qt.UserRole) or "") for item in self.project_list.selectedItems()]
        intake_item_ids = [str(item.data(Qt.UserRole) or "") for item in self.intake_list.selectedItems()]
        try:
            self._portfolio_service.create_scenario(
                name=self.scenario_name.text(),
                budget_limit=(None if self.scenario_budget.value() <= 0 else float(self.scenario_budget.value())),
                capacity_limit_percent=(
                    None if self.scenario_capacity.value() <= 0 else float(self.scenario_capacity.value())
                ),
                project_ids=project_ids,
                intake_item_ids=intake_item_ids,
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

    def _load_selected_scenario(self) -> None:
        scenario_id = self._selected_scenario_id()
        if not scenario_id:
            return
        scenarios = {scenario.id: scenario for scenario in self._portfolio_service.list_scenarios()}
        scenario = scenarios.get(scenario_id)
        if scenario is None:
            return
        self.scenario_name.setText(scenario.name)
        self.scenario_budget.setValue(float(scenario.budget_limit or 0.0))
        self.scenario_capacity.setValue(float(scenario.capacity_limit_percent or 0.0))
        self._apply_selection(self.project_list, set(scenario.project_ids))
        self._apply_selection(self.intake_list, set(scenario.intake_item_ids))

    def _selected_scenario_id(self) -> str:
        row = self.scenario_table.currentRow()
        if row < 0:
            return ""
        item = self.scenario_table.item(row, 0)
        return str(item.data(Qt.UserRole) or "") if item is not None else ""

    def _on_domain_change(self, _payload: str) -> None:
        self.reload_data()

    @staticmethod
    def _apply_selection(widget: QListWidget, selected_ids: set[str]) -> None:
        for idx in range(widget.count()):
            item = widget.item(idx)
            item.setSelected(str(item.data(Qt.UserRole) or "") in selected_ids)

    @staticmethod
    def _score_spin() -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(1, 5)
        spin.setValue(3)
        return spin


__all__ = ["PortfolioTab"]
