from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QGridLayout, QGroupBox, QHBoxLayout,
                               QLabel, QPushButton, QSplitter, QVBoxLayout,
                               QWidget)
from core.events.domain_events import domain_events
from core.services.auth import UserSessionContext
from core.services.baseline import BaselineService
from core.services.dashboard import DashboardData, DashboardService
from core.services.project import ProjectService
from ui.dashboard.access import (
    configure_dashboard_access,
    wire_dashboard_access,
)
from ui.dashboard.alerts_panel import DashboardAlertsPanelMixin
from ui.dashboard.data_ops import DashboardDataOpsMixin
from ui.dashboard.leveling_ops import DashboardLevelingOpsMixin
from ui.dashboard.rendering import DashboardRenderingMixin
from ui.dashboard.workqueue_button import DashboardQueueButton
from ui.dashboard.workqueue_actions import DashboardWorkqueueActionsMixin
from ui.dashboard.styles import (
    dashboard_action_button_style,
    dashboard_meta_chip_style, dashboard_summary_style,
)
from ui.dashboard.widgets import ChartWidget, KpiCard
from ui.styles.ui_config import UIConfig as CFG


class DashboardTab(
    DashboardDataOpsMixin,
    DashboardLevelingOpsMixin,
    DashboardRenderingMixin,
    DashboardAlertsPanelMixin,
    DashboardWorkqueueActionsMixin,
    QWidget,
):
    def __init__(
        self,
        project_service: ProjectService,
        dashboard_service: DashboardService,
        baseline_service: BaselineService,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._project_service: ProjectService = project_service
        self._dashboard_service: DashboardService = dashboard_service
        self._baseline_service: BaselineService = baseline_service
        configure_dashboard_access(self, user_session)
        self._current_data: Optional[DashboardData] = None
        self._current_conflicts = []
        self._current_alert_rows: list[tuple[str, str, str]] = []
        self._current_alert_summary: str = "0 active alerts"
        self._current_upcoming_rows: list[dict[str, object]] = []
        self._conflicts_dialog = None
        self._alerts_dialog = None
        self._upcoming_dialog = None
        self._setup_ui()
        self.reload_projects()
        domain_events.costs_changed.connect(self._on_domain_changed)
        domain_events.tasks_changed.connect(self._on_domain_changed)
        domain_events.project_changed.connect(self._on_project_catalog_changed)
        domain_events.resources_changed.connect(self._on_resources_changed)
        domain_events.baseline_changed.connect(self._on_baseline_changed)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_SM)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        top_bar = QWidget()
        top_bar.setStyleSheet(dashboard_summary_style())
        top = QHBoxLayout(top_bar)
        top.setContentsMargins(CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM)
        top.setSpacing(CFG.SPACING_SM)
        top.addWidget(QLabel("Project:"))

        self.project_combo = QComboBox()
        self.project_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.project_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.project_combo.setEditable(False)
        self.project_combo.setMaxVisibleItems(CFG.COMBO_MAX_VISIBLE)

        self.btn_reload_projects = QPushButton(CFG.RELOAD_BUTTON_LABEL)
        self.btn_refresh_dashboard = QPushButton(CFG.REFRESH_DASHBOARD_LABEL)
        self.btn_open_conflicts = DashboardQueueButton("Conflicts", active_variant="danger")
        self.btn_open_alerts = DashboardQueueButton("Alerts", active_variant="warning")
        self.btn_open_upcoming = DashboardQueueButton("Upcoming", active_variant="info")

        self.baseline_combo = QComboBox()
        self.baseline_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.baseline_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.baseline_combo.setEditable(False)
        self.baseline_combo.setMaxVisibleItems(CFG.COMBO_MAX_VISIBLE)

        self.btn_create_baseline = QPushButton(CFG.CREATE_BASELINE_LABEL)
        self.btn_delete_baseline = QPushButton(CFG.DELETE_BASELINE_LABEL)

        for btn in (
            self.btn_reload_projects,
            self.btn_refresh_dashboard,
            self.btn_open_conflicts,
            self.btn_open_alerts,
            self.btn_open_upcoming,
            self.btn_create_baseline,
            self.btn_delete_baseline,
        ):
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)

        self.btn_refresh_dashboard.setStyleSheet(dashboard_action_button_style("primary"))
        self.btn_reload_projects.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_open_conflicts.set_variants(active="danger", inactive="success")
        self.btn_open_alerts.set_variants(active="warning", inactive="success")
        self.btn_open_upcoming.set_variants(active="info", inactive="neutral")
        self.btn_create_baseline.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_delete_baseline.setStyleSheet(dashboard_action_button_style("danger"))

        top.addWidget(self.project_combo)
        top.addWidget(self.btn_reload_projects)
        top.addWidget(self.btn_refresh_dashboard)
        top.addWidget(self.btn_open_conflicts)
        top.addWidget(self.btn_open_alerts)
        top.addWidget(self.btn_open_upcoming)
        top.addStretch()
        top.addWidget(QLabel("Baseline:"))
        top.addWidget(self.baseline_combo)
        top.addWidget(self.btn_create_baseline)
        top.addWidget(self.btn_delete_baseline)
        layout.addWidget(top_bar)

        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(8)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(CFG.SPACING_SM)
        left_panel.setMinimumWidth(420)

        self.summary_widget = QWidget()
        self.summary_widget.setStyleSheet(dashboard_summary_style())
        s_layout = QVBoxLayout(self.summary_widget)
        s_layout.setContentsMargins(CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM)
        s_layout.setSpacing(CFG.SPACING_SM)

        title_row = QWidget()
        pt_layout = QHBoxLayout(title_row)
        pt_layout.setContentsMargins(0, 0, 0, 0)
        pt_layout.setSpacing(CFG.SPACING_XS)

        self.project_label_prefix = QLabel(CFG.DASHBOARD_PROJECT_LABEL)
        self.project_label_prefix.setStyleSheet(CFG.DASHBOARD_PROJECT_LABEL_STYLE)
        self.project_label_prefix.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.project_title_lbl = QLabel("Select a project to see schedule and cost health.")
        self.project_title_lbl.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        self.project_title_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.project_title_lbl.setWordWrap(True)
        self.project_title_lbl.setMinimumWidth(220)

        pt_layout.addWidget(self.project_label_prefix)
        pt_layout.addWidget(self.project_title_lbl)
        pt_layout.addStretch()

        meta_row = QWidget()
        meta_layout = QHBoxLayout(meta_row)
        meta_layout.setContentsMargins(0, 0, 0, 0)
        meta_layout.setSpacing(CFG.SPACING_XS)

        self.project_meta_start = QLabel("")
        self.project_meta_end = QLabel("")
        self.project_meta_duration = QLabel("")

        chip_style = dashboard_meta_chip_style()
        self.project_meta_start.setStyleSheet(chip_style)
        self.project_meta_end.setStyleSheet(chip_style)
        self.project_meta_duration.setStyleSheet(chip_style)

        meta_layout.addWidget(self.project_meta_start)
        meta_layout.addWidget(self.project_meta_end)
        meta_layout.addWidget(self.project_meta_duration)
        meta_layout.addStretch()

        s_layout.addWidget(title_row)
        s_layout.addWidget(meta_row)

        left_layout.addWidget(self.summary_widget)

        kpi_group = QGroupBox("Portfolio Summary")
        kpi_layout = QGridLayout(kpi_group)
        kpi_layout.setContentsMargins(CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM)
        kpi_layout.setSpacing(CFG.SPACING_SM)

        self.kpi_tasks = KpiCard("Tasks", "0 / 0", "Completed / Total")
        self.kpi_critical = KpiCard("Critical tasks", "0", "", CFG.COLOR_WARNING)
        self.kpi_late = KpiCard("Late tasks", "0", "", CFG.COLOR_DANGER)
        self.kpi_cost = KpiCard("Cost variance", "0.00", "Actual - Planned", CFG.COLOR_ACCENT)
        self.kpi_progress = KpiCard("% complete", "0%", "", CFG.COLOR_SUCCESS)

        kpi_layout.addWidget(self.kpi_tasks, 0, 0)
        kpi_layout.addWidget(self.kpi_critical, 0, 1)
        kpi_layout.addWidget(self.kpi_late, 0, 2)
        kpi_layout.addWidget(self.kpi_cost, 1, 0, 1, 2)
        kpi_layout.addWidget(self.kpi_progress, 1, 2)
        kpi_layout.setColumnStretch(0, 1)
        kpi_layout.setColumnStretch(1, 1)
        kpi_layout.setColumnStretch(2, 1)
        left_layout.addWidget(kpi_group)

        self.evm_group = self._build_evm_panel()
        left_layout.addWidget(self.evm_group, 1)

        self._prepare_conflicts_dialog()

        right_panel = QWidget()
        right_panel.setMinimumWidth(360)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(CFG.SPACING_SM)

        self.chart_splitter = QSplitter(Qt.Vertical)
        self.chart_splitter.setChildrenCollapsible(False)
        self.chart_splitter.setHandleWidth(8)
        self.burndown_chart = ChartWidget("Burndown (remaining tasks)")
        self.resource_chart = ChartWidget("Resource load (allocation %)")
        self.chart_splitter.addWidget(self.burndown_chart)
        self.chart_splitter.addWidget(self.resource_chart)
        self.chart_splitter.setStretchFactor(0, 1)
        self.chart_splitter.setStretchFactor(1, 1)
        right_layout.addWidget(self.chart_splitter)

        self.main_splitter.addWidget(left_panel)
        self.main_splitter.addWidget(right_panel)
        self.main_splitter.setStretchFactor(0, 5)
        self.main_splitter.setStretchFactor(1, 5)
        self.main_splitter.setSizes([700, 700])
        layout.addWidget(self.main_splitter, 1)

        self.btn_reload_projects.clicked.connect(self.reload_projects)
        self.btn_refresh_dashboard.clicked.connect(self.refresh_dashboard)
        self.btn_open_conflicts.clicked.connect(self._open_conflicts_dialog)
        self.btn_open_alerts.clicked.connect(self._open_alerts_dialog)
        self.btn_open_upcoming.clicked.connect(self._open_upcoming_dialog)
        self.btn_create_baseline.clicked.connect(self._generate_baseline)
        self.btn_delete_baseline.clicked.connect(self._delete_selected_baseline)
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)
        self.baseline_combo.currentIndexChanged.connect(self.refresh_dashboard)
        wire_dashboard_access(self)
