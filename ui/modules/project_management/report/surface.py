from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ui.modules.project_management.dashboard.styles import dashboard_action_button_style, dashboard_badge_style, dashboard_meta_chip_style
from src.ui.shared.widgets.guards import make_guarded_slot
from src.ui.shared.formatting.ui_config import UIConfig as CFG


class ReportSurfaceMixin:
    project_combo: QComboBox
    btn_reload_projects: QPushButton
    btn_load_kpi: QPushButton
    btn_show_gantt: QPushButton
    btn_show_critical: QPushButton
    btn_show_resource_load: QPushButton
    btn_show_performance: QPushButton
    btn_show_evm: QPushButton
    btn_show_finance: QPushButton
    btn_show_baseline_compare: QPushButton
    btn_export_gantt: QPushButton
    btn_export_evm: QPushButton
    btn_export_excel: QPushButton
    btn_export_pdf: QPushButton
    _finance_service: object | None
    _user_session: object | None

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        header = QWidget()
        self.report_header_card = header
        header.setObjectName("reportHeaderCard")
        header.setSizePolicy(CFG.H_EXPAND_V_FIXED)
        header.setStyleSheet(
            f"QWidget#reportHeaderCard {{ background-color: {CFG.COLOR_BG_SURFACE}; border: 1px solid {CFG.COLOR_BORDER}; border-radius: 12px; }}"
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_SM, CFG.MARGIN_MD, CFG.MARGIN_SM)
        header_layout.setSpacing(CFG.SPACING_MD)
        header_layout.setAlignment(Qt.AlignTop)
        intro = QVBoxLayout()
        intro.setSpacing(CFG.SPACING_XS)
        eyebrow = QLabel("REPORTS")
        eyebrow.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
        title = QLabel("Reporting Center")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        subtitle = QLabel("Operational and executive reporting for schedule, risk, cost, and earned value.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        subtitle.setMaximumWidth(760)
        for widget in (eyebrow, title, subtitle):
            intro.addWidget(widget)
        header_layout.addLayout(intro, 1)
        status_layout = QVBoxLayout()
        status_layout.setSpacing(CFG.SPACING_SM)
        self.report_project_badge = QLabel("No Project")
        self.report_project_badge.setStyleSheet(dashboard_badge_style(CFG.COLOR_ACCENT))
        self.report_finance_badge = QLabel("Finance Ready" if self._finance_service is not None else "Finance Off")
        self.report_finance_badge.setStyleSheet(dashboard_meta_chip_style())
        self.report_export_badge = QLabel("On-screen only")
        self.report_export_badge.setStyleSheet(dashboard_meta_chip_style())
        status_layout.addWidget(self.report_project_badge, 0, Qt.AlignRight)
        status_layout.addWidget(self.report_finance_badge, 0, Qt.AlignRight)
        status_layout.addWidget(self.report_export_badge, 0, Qt.AlignRight)
        status_layout.addStretch(1)
        header_layout.addLayout(status_layout)
        layout.addWidget(header)

        controls = QWidget()
        self.report_controls_card = controls
        controls.setObjectName("reportControlSurface")
        controls.setSizePolicy(CFG.H_EXPAND_V_FIXED)
        controls.setStyleSheet(
            f"QWidget#reportControlSurface {{ background-color: {CFG.COLOR_BG_SURFACE_ALT}; border: 1px solid {CFG.COLOR_BORDER}; border-radius: 12px; }}"
        )
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM)
        controls_layout.setSpacing(CFG.SPACING_SM)
        controls_layout.addWidget(QLabel("Project"))
        self.project_combo = QComboBox()
        self.project_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.project_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.project_combo.setMinimumWidth(280)
        self.project_combo.setEditable(False)
        self.btn_reload_projects = QPushButton(CFG.RELOAD_BUTTON_LABEL)
        self.btn_reload_projects.setMinimumHeight(CFG.BUTTON_HEIGHT)
        self.btn_reload_projects.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_reload_projects.setToolTip("Reload projects from the latest database state.")
        self.btn_reload_projects.setStyleSheet(dashboard_action_button_style("secondary"))
        controls_layout.addWidget(self.project_combo, 1)
        controls_layout.addWidget(self.btn_reload_projects)
        layout.addWidget(controls)

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
        self.btn_show_finance = QPushButton("Show Finance View")
        self.btn_show_baseline_compare = QPushButton(CFG.SHOW_BASELINE_COMPARE_LABEL)
        view_buttons = [
            self.btn_load_kpi,
            self.btn_show_gantt,
            self.btn_show_critical,
            self.btn_show_resource_load,
            self.btn_show_performance,
            self.btn_show_evm,
            self.btn_show_baseline_compare,
            self.btn_show_finance,
        ]
        for index, btn in enumerate(view_buttons):
            btn.setMinimumHeight(CFG.BUTTON_HEIGHT)
            btn.setMinimumWidth(190)
            btn.setSizePolicy(CFG.H_EXPAND_V_FIXED)
            btn.setStyleSheet(dashboard_action_button_style("primary" if index == 0 else "secondary"))
        tips = {
            self.btn_load_kpi: "High-level KPI snapshot for schedule, tasks, and cost.",
            self.btn_show_gantt: "Timeline chart for planned and ongoing work.",
            self.btn_show_critical: "Critical path view for dependency-sensitive work.",
            self.btn_show_resource_load: "Resource loading overview by assignment pressure.",
            self.btn_show_performance: "Schedule variance and cost variance against baseline.",
            self.btn_show_evm: "Earned Value metrics and trend for project controls.",
            self.btn_show_finance: "Ledger, cashflow/forecast, and expense analytics view.",
            self.btn_show_baseline_compare: "Compare two baselines to review task-level planning drift.",
        }
        for btn, tip in tips.items():
            btn.setToolTip(tip)
        for row, col, btn in (
            (0, 0, self.btn_load_kpi),
            (0, 1, self.btn_show_gantt),
            (0, 2, self.btn_show_critical),
            (1, 0, self.btn_show_resource_load),
            (1, 1, self.btn_show_performance),
            (1, 2, self.btn_show_evm),
            (2, 0, self.btn_show_baseline_compare),
            (2, 1, self.btn_show_finance),
        ):
            ons_layout.addWidget(btn, row, col)
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
        for index, btn in enumerate((self.btn_export_gantt, self.btn_export_evm, self.btn_export_excel, self.btn_export_pdf)):
            btn.setMinimumHeight(CFG.BUTTON_HEIGHT)
            btn.setMinimumWidth(170)
            btn.setSizePolicy(CFG.H_EXPAND_V_FIXED)
            btn.setStyleSheet(dashboard_action_button_style("primary" if index == 3 else "secondary"))
        self.btn_export_gantt.setToolTip("Save the Gantt chart as a PNG image.")
        self.btn_export_evm.setToolTip("Save the EVM PV/EV/AC trend chart as PNG.")
        self.btn_export_excel.setToolTip("Export KPIs, tasks, and resource load as an Excel workbook.")
        self.btn_export_pdf.setToolTip("Generate a PDF report with KPIs, Gantt chart, and resource load.")
        for btn in (self.btn_export_gantt, self.btn_export_evm, self.btn_export_excel, self.btn_export_pdf):
            exp_layout.addWidget(btn)
        layout.addWidget(group_export)
        layout.addStretch(1)

        self.btn_reload_projects.clicked.connect(make_guarded_slot(self, title="Reports", callback=self._load_projects))
        self.project_combo.currentIndexChanged.connect(self._on_report_project_changed_ui)
        for btn, callback in (
            (self.btn_load_kpi, self.load_kpis),
            (self.btn_show_gantt, self.show_gantt),
            (self.btn_show_critical, self.show_critical_path),
            (self.btn_show_resource_load, self.show_resource_load),
            (self.btn_show_performance, self.show_performance),
            (self.btn_show_evm, self.show_evm),
            (self.btn_show_finance, self.show_finance),
            (self.btn_export_gantt, self.export_gantt_png),
            (self.btn_export_evm, self.export_evm_png),
            (self.btn_export_excel, self.export_excel),
            (self.btn_export_pdf, self.export_pdf),
        ):
            btn.clicked.connect(make_guarded_slot(self, title="Reports", callback=callback))
        self.btn_show_baseline_compare.clicked.connect(self.show_baseline_comparison)
        self._apply_permissions()

    def _apply_permissions(self) -> None:
        self.btn_show_finance.setEnabled(self._finance_service is not None)
        can_export = bool(
            self._user_session is not None and self._user_session.has_permission("report.export")
        )
        for btn in (self.btn_export_gantt, self.btn_export_evm, self.btn_export_excel, self.btn_export_pdf):
            btn.setEnabled(can_export)
        self._update_report_header_badges()

    def _on_report_project_changed_ui(self, _index: int) -> None:
        self._update_report_header_badges()

    def _update_report_header_badges(self) -> None:
        self.report_project_badge.setText(self.project_combo.currentText().strip() or "No Project")
        self.report_finance_badge.setText("Finance Ready" if self._finance_service is not None else "Finance Off")
        can_export = bool(
            self._user_session is not None and self._user_session.has_permission("report.export")
        )
        self.report_export_badge.setText("Export Enabled" if can_export else "On-screen only")
