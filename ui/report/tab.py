from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.events.domain_events import domain_events
from core.services.project import ProjectService
from core.services.reporting import ReportingService
from core.services.auth import UserSessionContext
from ui.report.actions import ReportActionsMixin
from ui.report.project_flow import ReportProjectFlowMixin
from ui.shared.guards import make_guarded_slot
from ui.styles.ui_config import UIConfig as CFG


class ReportTab(ReportProjectFlowMixin, ReportActionsMixin, QWidget):
    """Report tab coordinator: UI layout and event wiring only."""

    def __init__(
        self,
        project_service: ProjectService,
        reporting_service: ReportingService,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._project_service: ProjectService = project_service
        self._reporting_service: ReportingService = reporting_service
        self._user_session = user_session
        self._setup_ui()
        self._load_projects()
        domain_events.project_changed.connect(self._on_project_changed_event)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_LG, CFG.MARGIN_LG, CFG.MARGIN_LG, CFG.MARGIN_LG)

        title = QLabel("Reporting Center")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        subtitle = QLabel(
            "Operational and executive reporting for schedule, risk, cost, and earned value."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        selector_card = QFrame()
        selector_card.setStyleSheet(CFG.PROJECT_SUMMARY_BOX_STYLE)
        selector_layout = QHBoxLayout(selector_card)
        selector_layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        selector_layout.setSpacing(CFG.SPACING_SM)

        selector_label = QLabel("Project")
        selector_label.setStyleSheet(CFG.DASHBOARD_PROJECT_LABEL_STYLE)
        selector_layout.addWidget(selector_label)

        self.project_combo = QComboBox()
        self.project_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.project_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.project_combo.setMinimumWidth(300)
        self.project_combo.setEditable(False)
        self.btn_reload_projects = QPushButton(CFG.RELOAD_BUTTON_LABEL)
        self.btn_reload_projects.setMinimumHeight(CFG.BUTTON_HEIGHT)
        self.btn_reload_projects.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_reload_projects.setMinimumWidth(120)
        self.btn_reload_projects.setToolTip("Reload projects from the latest database state.")
        selector_layout.addWidget(self.project_combo, 1)
        selector_layout.addWidget(self.btn_reload_projects)
        layout.addWidget(selector_card)

        group_on_screen = QGroupBox("Operational Views")
        group_on_screen.setFont(CFG.GROUPBOX_TITLE_FONT)
        ons_layout = QGridLayout(group_on_screen)
        ons_layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        ons_layout.setHorizontalSpacing(CFG.SPACING_MD)
        ons_layout.setVerticalSpacing(CFG.SPACING_SM)

        self.btn_load_kpi = QPushButton(CFG.SHOW_KPIS_LABEL)
        self.btn_show_gantt = QPushButton(CFG.SHOW_GANTT_LABEL)
        self.btn_show_critical = QPushButton(CFG.SHOW_CRITICAL_PATH_LABEL)
        self.btn_show_resource_load = QPushButton(CFG.SHOW_RESOURCE_LOAD_LABEL)
        self.btn_show_performance = QPushButton("Show Performance Variance")
        self.btn_show_evm = QPushButton("Show EVM Analysis")
        self.btn_show_baseline_compare = QPushButton(CFG.SHOW_BASELINE_COMPARE_LABEL)
        for btn in [
            self.btn_load_kpi,
            self.btn_show_gantt,
            self.btn_show_critical,
            self.btn_show_resource_load,
            self.btn_show_performance,
            self.btn_show_evm,
            self.btn_show_baseline_compare,
        ]:
            btn.setMinimumHeight(CFG.BUTTON_HEIGHT)
            btn.setMinimumWidth(190)
            btn.setSizePolicy(CFG.H_EXPAND_V_FIXED)

        self.btn_load_kpi.setToolTip("High-level KPI snapshot for schedule, tasks, and cost.")
        self.btn_show_gantt.setToolTip("Timeline chart for planned and ongoing work.")
        self.btn_show_critical.setToolTip("Critical path view for dependency-sensitive work.")
        self.btn_show_resource_load.setToolTip("Resource loading overview by assignment pressure.")
        self.btn_show_performance.setToolTip("Schedule variance and cost variance against baseline.")
        self.btn_show_evm.setToolTip("Earned Value metrics and trend for project controls.")
        self.btn_show_baseline_compare.setToolTip("Compare two baselines to review task-level planning drift.")

        ons_layout.addWidget(self.btn_load_kpi, 0, 0)
        ons_layout.addWidget(self.btn_show_gantt, 0, 1)
        ons_layout.addWidget(self.btn_show_critical, 0, 2)
        ons_layout.addWidget(self.btn_show_resource_load, 1, 0)
        ons_layout.addWidget(self.btn_show_performance, 1, 1)
        ons_layout.addWidget(self.btn_show_evm, 1, 2)
        ons_layout.addWidget(self.btn_show_baseline_compare, 2, 0)
        for col in range(3):
            ons_layout.setColumnStretch(col, 1)
        layout.addWidget(group_on_screen)

        group_export = QGroupBox("Executive Exports")
        group_export.setFont(CFG.GROUPBOX_TITLE_FONT)
        exp_layout = QHBoxLayout(group_export)
        exp_layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        exp_layout.setSpacing(CFG.SPACING_SM)
        self.btn_export_gantt = QPushButton(CFG.EXPORT_GANTT_LABEL)
        self.btn_export_evm = QPushButton("Export EVM (PNG)")
        self.btn_export_excel = QPushButton(CFG.EXPORT_EXCEL_LABEL)
        self.btn_export_pdf = QPushButton(CFG.EXPORT_PDF_LABEL)
        for btn in [self.btn_export_gantt, self.btn_export_evm, self.btn_export_excel, self.btn_export_pdf]:
            btn.setMinimumHeight(CFG.BUTTON_HEIGHT)
            btn.setMinimumWidth(170)
            btn.setSizePolicy(CFG.H_EXPAND_V_FIXED)
        self.btn_export_gantt.setToolTip("Save the Gantt chart as a PNG image.")
        self.btn_export_evm.setToolTip("Save the EVM PV/EV/AC trend chart as PNG.")
        self.btn_export_excel.setToolTip("Export KPIs, tasks, and resource load as an Excel workbook.")
        self.btn_export_pdf.setToolTip("Generate a PDF report with KPIs, Gantt chart, and resource load.")
        exp_layout.addWidget(self.btn_export_gantt)
        exp_layout.addWidget(self.btn_export_evm)
        exp_layout.addWidget(self.btn_export_excel)
        exp_layout.addWidget(self.btn_export_pdf)
        layout.addWidget(group_export)

        coverage = QLabel(
            "Coverage includes KPI status, critical path, resource load, baseline variance, baseline comparison, and EVM.\n"
            "Reports are generated from live scheduling, assignment, and cost data."
        )
        coverage.setWordWrap(True)
        coverage.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        coverage.setStyleSheet(CFG.INFO_TEXT_STYLE)
        layout.addWidget(coverage)
        layout.addStretch()

        self.btn_reload_projects.clicked.connect(
            make_guarded_slot(self, title="Reports", callback=self._load_projects)
        )
        self.btn_load_kpi.clicked.connect(
            make_guarded_slot(self, title="Reports", callback=self.load_kpis)
        )
        self.btn_show_gantt.clicked.connect(
            make_guarded_slot(self, title="Reports", callback=self.show_gantt)
        )
        self.btn_show_critical.clicked.connect(
            make_guarded_slot(self, title="Reports", callback=self.show_critical_path)
        )
        self.btn_show_resource_load.clicked.connect(
            make_guarded_slot(self, title="Reports", callback=self.show_resource_load)
        )
        self.btn_show_performance.clicked.connect(
            make_guarded_slot(self, title="Reports", callback=self.show_performance)
        )
        self.btn_show_evm.clicked.connect(
            make_guarded_slot(self, title="Reports", callback=self.show_evm)
        )
        self.btn_show_baseline_compare.clicked.connect(self.show_baseline_comparison)
        self.btn_export_gantt.clicked.connect(
            make_guarded_slot(self, title="Reports", callback=self.export_gantt_png)
        )
        self.btn_export_evm.clicked.connect(
            make_guarded_slot(self, title="Reports", callback=self.export_evm_png)
        )
        self.btn_export_excel.clicked.connect(
            make_guarded_slot(self, title="Reports", callback=self.export_excel)
        )
        self.btn_export_pdf.clicked.connect(
            make_guarded_slot(self, title="Reports", callback=self.export_pdf)
        )
        self._apply_permissions()

    def _apply_permissions(self) -> None:
        if self._user_session is None:
            return
        can_export = self._user_session.has_permission("report.export")
        self.btn_export_gantt.setEnabled(can_export)
        self.btn_export_evm.setEnabled(can_export)
        self.btn_export_excel.setEnabled(can_export)
        self.btn_export_pdf.setEnabled(can_export)
