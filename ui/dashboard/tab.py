from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from core.events.domain_events import domain_events
from core.services.baseline import BaselineService
from core.services.dashboard import DashboardData, DashboardService
from core.services.project import ProjectService
from ui.dashboard.data_ops import DashboardDataOpsMixin
from ui.dashboard.rendering import DashboardRenderingMixin
from ui.dashboard.widgets import ChartWidget, KpiCard
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG


class DashboardTab(DashboardDataOpsMixin, DashboardRenderingMixin, QWidget):
    """
    Dashboard coordinator:
    - wires UI
    - delegates loading/state actions to DashboardDataOpsMixin
    - delegates rendering/update logic to DashboardRenderingMixin
    """

    def __init__(
        self,
        project_service: ProjectService,
        dashboard_service: DashboardService,
        baseline_service: BaselineService,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._project_service = project_service
        self._dashboard_service = dashboard_service
        self._baseline_service = baseline_service

        self._current_data: Optional[DashboardData] = None

        self._setup_ui()
        self.reload_projects()
        domain_events.costs_changed.connect(self._on_domain_changed)
        domain_events.tasks_changed.connect(self._on_domain_changed)
        domain_events.project_changed.connect(self._on_domain_changed)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_XS)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        top = QHBoxLayout()
        top.addSpacing(CFG.SPACING_MD)
        top.addWidget(QLabel("Project:"))
        self.project_combo = QComboBox()
        self.project_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.project_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.project_combo.setEditable(CFG.COMBO_EDITABLE)
        self.project_combo.setMaxVisibleItems(CFG.COMBO_MAX_VISIBLE)

        self.btn_reload_projects = QPushButton(CFG.RELOAD_BUTTON_LABEL)
        self.btn_refresh_dashboard = QPushButton(CFG.REFRESH_DASHBOARD_LABEL)

        self.baseline_combo = QComboBox()
        self.baseline_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.baseline_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.baseline_combo.setEditable(CFG.COMBO_EDITABLE)
        self.baseline_combo.setMaxVisibleItems(CFG.COMBO_MAX_VISIBLE)

        self.btn_create_baseline = QPushButton(CFG.CREATE_BASELINE_LABEL)
        self.btn_delete_baseline = QPushButton(CFG.DELETE_BASELINE_LABEL)

        for btn in (
            self.btn_reload_projects,
            self.btn_refresh_dashboard,
            self.btn_create_baseline,
            self.btn_delete_baseline,
        ):
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)

        top.addWidget(self.project_combo)
        top.addWidget(self.btn_reload_projects)
        top.addWidget(self.btn_refresh_dashboard)
        top.addStretch()
        top.addWidget(QLabel("Baseline:"))
        top.addWidget(self.baseline_combo)
        top.addWidget(self.btn_create_baseline)
        top.addWidget(self.btn_delete_baseline)
        layout.addLayout(top)

        self.summary_widget = QWidget()
        self.summary_widget.setStyleSheet(CFG.PROJECT_SUMMARY_BOX_STYLE)
        s_layout = QHBoxLayout(self.summary_widget)
        s_layout.setContentsMargins(CFG.SPACING_XS, CFG.SPACING_XS, CFG.SPACING_XS, CFG.SPACING_XS)
        s_layout.setSpacing(CFG.SPACING_SM)

        self.prefix_title_widget = QWidget()
        pt_layout = QHBoxLayout(self.prefix_title_widget)
        pt_layout.setContentsMargins(0, 0, 0, 0)
        pt_layout.setSpacing(CFG.SPACING_XS)
        self.prefix_title_widget.setSizePolicy(CFG.FIXED_BOTH)

        self.project_label_prefix = QLabel(CFG.DASHBOARD_PROJECT_LABEL)
        self.project_label_prefix.setStyleSheet(CFG.DASHBOARD_PROJECT_LABEL_STYLE)
        self.project_label_prefix.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.project_label_prefix.setFixedHeight(CFG.DASHBOARD_PROJECT_ITEM_HEIGHT)

        self.project_title_lbl = QLabel("")
        self.project_title_lbl.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        self.project_title_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.project_title_lbl.setMinimumWidth(160)
        self.project_title_lbl.setFixedHeight(CFG.DASHBOARD_PROJECT_ITEM_HEIGHT)

        pt_layout.addWidget(self.project_label_prefix)
        pt_layout.addWidget(self.project_title_lbl)
        self.project_title_lbl.setMaximumWidth(300)

        meta_widget = QWidget()
        meta_layout = QHBoxLayout(meta_widget)
        meta_layout.setContentsMargins(0, 0, 0, 0)
        meta_layout.setSpacing(CFG.SPACING_XS)

        self.project_meta_start = QLabel("")
        self.project_meta_start.setStyleSheet(CFG.DASHBOARD_PROJECT_META_STYLE)
        self.project_meta_start.setFixedHeight(CFG.DASHBOARD_PROJECT_ITEM_HEIGHT)
        self.project_meta_end = QLabel("")
        self.project_meta_end.setStyleSheet(CFG.DASHBOARD_PROJECT_META_STYLE)
        self.project_meta_end.setFixedHeight(CFG.DASHBOARD_PROJECT_ITEM_HEIGHT)
        self.project_meta_duration = QLabel("")
        self.project_meta_duration.setStyleSheet(CFG.DASHBOARD_PROJECT_META_STYLE)
        self.project_meta_duration.setFixedHeight(CFG.DASHBOARD_PROJECT_ITEM_HEIGHT)

        meta_layout.addWidget(self.project_meta_start)
        meta_layout.addWidget(self.project_meta_end)
        meta_layout.addWidget(self.project_meta_duration)

        s_layout.addWidget(self.prefix_title_widget)
        s_layout.addSpacing(CFG.SPACING_XS)
        s_layout.addWidget(meta_widget)
        meta_widget.setSizePolicy(CFG.FIXED_BOTH)

        layout.addWidget(self.summary_widget)

        kpi_group = QGroupBox()
        kpi_layout = QHBoxLayout(kpi_group)
        kpi_layout.setSpacing(CFG.SPACING_XS)

        self.kpi_tasks = KpiCard("Tasks", "0 / 0", "Completed / Total")
        self.kpi_critical = KpiCard("Critical tasks", "0", "", "#f5a623")
        self.kpi_late = KpiCard("Late tasks", "0", "", "#d0021b")
        self.kpi_cost = KpiCard("Cost variance", "0.00", "Actual - Planned", "#4a90e2")
        self.kpi_progress = KpiCard("% complete", "0%", "", "#7ed321")

        kpi_layout.addWidget(self.kpi_tasks)
        kpi_layout.addWidget(self.kpi_critical)
        kpi_layout.addWidget(self.kpi_late)
        kpi_layout.addWidget(self.kpi_cost)
        kpi_layout.addWidget(self.kpi_progress)
        layout.addWidget(kpi_group)

        self.evm_group = self._build_evm_panel()
        layout.addWidget(self.evm_group)

        charts_row = QHBoxLayout()
        self.burndown_chart = ChartWidget("Burndown (remaining tasks)")
        self.resource_chart = ChartWidget("Resource load (allocation %)")
        charts_row.addWidget(self.burndown_chart)
        charts_row.addWidget(self.resource_chart)
        layout.addLayout(charts_row)

        bottom_row = QHBoxLayout()

        alerts_group = QGroupBox("Alerts")
        alerts_group.setFont(CFG.GROUPBOX_TITLE_FONT)
        alerts_layout = QVBoxLayout(alerts_group)
        self.alerts_list = QListWidget()
        alerts_layout.addWidget(self.alerts_list)
        bottom_row.addWidget(alerts_group, 1)

        upcoming_group = QGroupBox("Upcoming tasks (next 14 days)")
        upcoming_group.setFont(CFG.GROUPBOX_TITLE_FONT)
        up_layout = QVBoxLayout(upcoming_group)
        up_layout.addSpacing(CFG.SPACING_XS)

        self.upcoming_table = QTableWidget(0, len(CFG.UPCOMING_TASKS_HEADERS))
        self.upcoming_table.setHorizontalHeaderLabels(CFG.UPCOMING_TASKS_HEADERS)
        self.upcoming_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        style_table(self.upcoming_table)
        up_layout.addWidget(self.upcoming_table)
        bottom_row.addWidget(upcoming_group, 2)

        layout.addLayout(bottom_row)
        layout.addStretch()

        self.btn_reload_projects.clicked.connect(self.reload_projects)
        self.btn_refresh_dashboard.clicked.connect(self.refresh_dashboard)
        self.btn_create_baseline.clicked.connect(self._generate_baseline)
        self.btn_delete_baseline.clicked.connect(self._delete_selected_baseline)
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)
        self.baseline_combo.currentIndexChanged.connect(self.refresh_dashboard)
