from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.services.project import ProjectService
from core.services.reporting import ReportingService
from ui.report.actions import ReportActionsMixin
from ui.report.project_flow import ReportProjectFlowMixin
from ui.styles.ui_config import UIConfig as CFG


class ReportTab(ReportProjectFlowMixin, ReportActionsMixin, QWidget):
    """Report tab coordinator: UI layout and event wiring only."""

    def __init__(
        self,
        project_service: ProjectService,
        reporting_service: ReportingService,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._project_service: ProjectService = project_service
        self._reporting_service: ReportingService = reporting_service
        self._setup_ui()
        self._load_projects()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        self.setMinimumSize(self.sizeHint())

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Project:"))
        self.project_combo = QComboBox()
        self.project_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.project_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.btn_reload_projects = QPushButton(CFG.RELOAD_BUTTON_LABEL)
        top_row.addWidget(self.project_combo)
        top_row.addWidget(self.btn_reload_projects)
        top_row.addStretch()
        layout.addLayout(top_row)

        group_on_screen = QGroupBox("On-screen reports")
        group_on_screen.setFont(CFG.GROUPBOX_TITLE_FONT)
        ons_layout = QHBoxLayout(group_on_screen)
        ons_layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        self.btn_load_kpi = QPushButton(CFG.SHOW_KPIS_LABEL)
        self.btn_show_gantt = QPushButton(CFG.SHOW_GANTT_LABEL)
        self.btn_show_critical = QPushButton(CFG.SHOW_CRITICAL_PATH_LABEL)
        self.btn_show_resource_load = QPushButton(CFG.SHOW_RESOURCE_LOAD_LABEL)
        for btn in [
            self.btn_reload_projects,
            self.btn_load_kpi,
            self.btn_show_gantt,
            self.btn_show_critical,
            self.btn_show_resource_load,
        ]:
            btn.setMinimumHeight(CFG.BUTTON_HEIGHT)
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_load_kpi.setToolTip("Open a dialog with key project indicators.")
        self.btn_show_gantt.setToolTip("Preview the Gantt chart inside the application.")
        self.btn_show_critical.setToolTip("See the list of critical path tasks.")
        self.btn_show_resource_load.setToolTip("See how busy each resource is on this project.")
        ons_layout.addWidget(self.btn_load_kpi)
        ons_layout.addWidget(self.btn_show_gantt)
        ons_layout.addWidget(self.btn_show_critical)
        ons_layout.addWidget(self.btn_show_resource_load)
        ons_layout.addStretch()
        layout.addWidget(group_on_screen)

        group_export = QGroupBox("Export reports")
        group_export.setFont(CFG.GROUPBOX_TITLE_FONT)
        exp_layout = QHBoxLayout(group_export)
        exp_layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        self.btn_export_gantt = QPushButton(CFG.EXPORT_GANTT_LABEL)
        self.btn_export_excel = QPushButton(CFG.EXPORT_EXCEL_LABEL)
        self.btn_export_pdf = QPushButton(CFG.EXPORT_PDF_LABEL)
        for btn in [self.btn_export_gantt, self.btn_export_excel, self.btn_export_pdf]:
            btn.setMinimumHeight(CFG.BUTTON_HEIGHT)
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_export_gantt.setToolTip("Save the Gantt chart as a PNG image.")
        self.btn_export_excel.setToolTip("Export KPIs, tasks, and resource load as an Excel workbook.")
        self.btn_export_pdf.setToolTip("Generate a PDF report with KPIs, Gantt chart, and resource load.")
        exp_layout.addWidget(self.btn_export_gantt)
        exp_layout.addWidget(self.btn_export_excel)
        exp_layout.addWidget(self.btn_export_pdf)
        exp_layout.addStretch()
        layout.addWidget(group_export)

        info_label = QLabel(
            "Choose a project above, then either preview reports on screen or export them.\n"
            "Calendar settings and task changes will be reflected in all reports."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(CFG.INFO_TEXT_STYLE)
        layout.addWidget(info_label)
        layout.addStretch()

        self.btn_reload_projects.clicked.connect(self._load_projects)
        self.btn_load_kpi.clicked.connect(self.load_kpis)
        self.btn_show_gantt.clicked.connect(self.show_gantt)
        self.btn_show_critical.clicked.connect(self.show_critical_path)
        self.btn_show_resource_load.clicked.connect(self.show_resource_load)
        self.btn_export_gantt.clicked.connect(self.export_gantt_png)
        self.btn_export_excel.clicked.connect(self.export_excel)
        self.btn_export_pdf.clicked.connect(self.export_pdf)
