from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.events.domain_events import domain_events
from core.services.auth import UserSessionContext
from core.services.baseline import BaselineService
from core.services.dashboard import DashboardData, DashboardService
from core.services.project import ProjectService
from ui.dashboard.access import configure_dashboard_access, wire_dashboard_access
from ui.dashboard.alerts_panel import DashboardAlertsPanelMixin
from ui.dashboard.control_rail import DashboardControlRailMixin
from ui.dashboard.data_ops import DashboardDataOpsMixin
from ui.dashboard.layout_state import DashboardLayoutStateMixin
from ui.dashboard.leveling_ops import DashboardLevelingOpsMixin
from ui.dashboard.portfolio_panel import DashboardPortfolioPanelMixin
from ui.dashboard.rendering import DashboardRenderingMixin
from ui.dashboard.top_bar import DashboardTopBarMixin
from ui.dashboard.widgets import ChartWidget, KpiCard
from ui.dashboard.workqueue_button import DashboardQueueButton
from ui.dashboard.workqueue_actions import DashboardWorkqueueActionsMixin
from ui.settings.main_window_store import MainWindowSettingsStore
from ui.styles.ui_config import UIConfig as CFG


class DashboardTab(
    DashboardDataOpsMixin,
    DashboardLayoutStateMixin,
    DashboardLevelingOpsMixin,
    DashboardRenderingMixin,
    DashboardAlertsPanelMixin,
    DashboardWorkqueueActionsMixin,
    DashboardPortfolioPanelMixin,
    DashboardControlRailMixin,
    DashboardTopBarMixin,
    QWidget,
):
    def __init__(
        self,
        project_service: ProjectService,
        dashboard_service: DashboardService,
        baseline_service: BaselineService,
        settings_store: MainWindowSettingsStore | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._project_service: ProjectService = project_service
        self._dashboard_service: DashboardService = dashboard_service
        self._baseline_service: BaselineService = baseline_service
        self._settings_store = settings_store
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

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_SM)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        self.project_combo = QComboBox()
        self.project_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.project_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.project_combo.setEditable(False)
        self.project_combo.setMaxVisibleItems(CFG.COMBO_MAX_VISIBLE)

        self.btn_reload_projects = QPushButton(CFG.RELOAD_BUTTON_LABEL)
        self.btn_refresh_dashboard = QPushButton(CFG.REFRESH_DASHBOARD_LABEL)
        self.btn_customize_dashboard = QPushButton("Customize Dashboard")
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
            self.btn_customize_dashboard,
            self.btn_create_baseline,
            self.btn_delete_baseline,
        ):
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)

        self.summary_widget = self._build_dashboard_top_bar()
        layout.addWidget(self.summary_widget)
        self._build_dashboard_panels()

        self.panel_scroll = QScrollArea()
        self.panel_scroll.setWidgetResizable(True)
        self.panel_scroll.setFrameShape(QFrame.NoFrame)
        self.panel_canvas = QWidget()
        self.panel_grid = QGridLayout(self.panel_canvas)
        self.panel_grid.setContentsMargins(0, 0, 0, 0)
        self.panel_grid.setHorizontalSpacing(CFG.SPACING_SM)
        self.panel_grid.setVerticalSpacing(CFG.SPACING_SM)
        self.panel_scroll.setWidget(self.panel_canvas)

        workspace = QWidget()
        workspace_layout = QHBoxLayout(workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(CFG.SPACING_SM)
        workspace_layout.addWidget(self._build_dashboard_control_sidebar())
        workspace_layout.addWidget(self.panel_scroll, 1)
        layout.addWidget(workspace, 1)

        self.btn_reload_projects.clicked.connect(self.reload_projects)
        self.btn_refresh_dashboard.clicked.connect(self.refresh_dashboard)
        self.btn_customize_dashboard.clicked.connect(self._open_dashboard_layout_builder)
        self.btn_open_conflicts.clicked.connect(self._open_conflicts_dialog)
        self.btn_open_alerts.clicked.connect(self._open_alerts_dialog)
        self.btn_open_upcoming.clicked.connect(self._open_upcoming_dialog)
        self.btn_create_baseline.clicked.connect(self._generate_baseline)
        self.btn_delete_baseline.clicked.connect(self._delete_selected_baseline)
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)
        self.baseline_combo.currentIndexChanged.connect(self.refresh_dashboard)
        self._apply_persisted_dashboard_layout()
        wire_dashboard_access(self)

    def _build_dashboard_panels(self) -> None:
        self.kpi_group = QGroupBox("Key Metrics")
        kpi_layout = QGridLayout(self.kpi_group)
        kpi_layout.setContentsMargins(CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM)
        kpi_layout.setHorizontalSpacing(CFG.SPACING_SM)
        kpi_layout.setVerticalSpacing(CFG.SPACING_SM)

        self.kpi_tasks = KpiCard("Tasks", "0 / 0", "Done / Total")
        self.kpi_progress = KpiCard("Progress", "0%", "Completion", CFG.COLOR_SUCCESS)
        self.kpi_inflight = KpiCard("In flight", "0", "Active work", CFG.COLOR_ACCENT)
        self.kpi_blocked = KpiCard("Blocked", "0", "Needs action", CFG.COLOR_WARNING)
        self.kpi_critical = KpiCard("Critical", "0", "Path pressure", CFG.COLOR_WARNING)
        self.kpi_late = KpiCard("Late", "0", "Behind plan", CFG.COLOR_DANGER)
        self.kpi_cost = KpiCard("Cost variance", "0.00", "Actual - planned", CFG.COLOR_ACCENT)
        self.kpi_budget = KpiCard("Spend vs plan", "0 / 0", "Actual / planned", CFG.COLOR_SUCCESS)

        cards = [
            self.kpi_tasks,
            self.kpi_progress,
            self.kpi_inflight,
            self.kpi_blocked,
            self.kpi_critical,
            self.kpi_late,
            self.kpi_cost,
            self.kpi_budget,
        ]
        for idx, card in enumerate(cards):
            kpi_layout.addWidget(card, idx // 4, idx % 4)
        for col in range(4):
            kpi_layout.setColumnStretch(col, 1)

        self.portfolio_group = self._build_portfolio_panel()
        self.portfolio_group.setTitle("Portfolio Ranking")
        self.evm_group = self._build_evm_panel()
        self.burndown_chart = ChartWidget("Burndown (remaining tasks)")
        self.resource_chart = ChartWidget("Resource load (allocation %)")
        self._prepare_conflicts_dialog()


__all__ = ["DashboardTab"]
