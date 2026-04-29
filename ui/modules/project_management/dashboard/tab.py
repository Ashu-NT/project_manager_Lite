from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QResizeEvent, QShowEvent
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

from src.core.platform.notifications.domain_events import domain_events
from src.core.platform.auth import UserSessionContext
from src.core.modules.project_management.application.scheduling.baseline_service import (
    BaselineService,
)
from src.core.modules.project_management.application.dashboard import (
    DashboardData,
    DashboardService,
)
from src.core.modules.project_management.application.projects import ProjectService
from ui.modules.project_management.dashboard.access import configure_dashboard_access, wire_dashboard_access
from ui.modules.project_management.dashboard.alerts_panel import DashboardAlertsPanelMixin
from ui.modules.project_management.dashboard.control_rail import DashboardControlRailMixin
from ui.modules.project_management.dashboard.data_ops import DashboardDataOpsMixin
from ui.modules.project_management.dashboard.layout_state import DashboardLayoutStateMixin
from ui.modules.project_management.dashboard.leveling_ops import DashboardLevelingOpsMixin
from ui.modules.project_management.dashboard.portfolio_panel import DashboardPortfolioPanelMixin
from ui.modules.project_management.dashboard.professional_panel import DashboardProfessionalPanelMixin
from ui.modules.project_management.dashboard.rendering import DashboardRenderingMixin
from ui.modules.project_management.dashboard.top_bar import DashboardTopBarMixin
from ui.modules.project_management.dashboard.widgets import ChartWidget, KpiCard
from ui.modules.project_management.dashboard.workqueue_button import DashboardQueueButton
from ui.modules.project_management.dashboard.workqueue_actions import DashboardWorkqueueActionsMixin
from src.ui.platform.settings.main_window_store import MainWindowSettingsStore
from src.ui.shared.formatting.ui_config import UIConfig as CFG


class DashboardTab(
    DashboardDataOpsMixin,
    DashboardLayoutStateMixin,
    DashboardLevelingOpsMixin,
    DashboardRenderingMixin,
    DashboardAlertsPanelMixin,
    DashboardWorkqueueActionsMixin,
    DashboardProfessionalPanelMixin,
    DashboardPortfolioPanelMixin,
    DashboardControlRailMixin,
    DashboardTopBarMixin,
    QWidget,
):
    _PANEL_CANVAS_MAX_WIDTH = 1480

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
        self._user_session = user_session
        configure_dashboard_access(self, user_session)
        self._current_data: Optional[DashboardData] = None
        self._current_conflicts = []
        self._current_alert_rows: list[tuple[str, str, str]] = []
        self._current_alert_summary: str = "0 active alerts"
        self._current_upcoming_rows: list[dict[str, object]] = []
        self._conflicts_dialog = None
        self._alerts_dialog = None
        self._upcoming_dialog = None
        self._layout_sync_scheduled = False
        self._setup_ui()
        self.reload_projects()
        domain_events.domain_changed.connect(self._on_generic_domain_change)

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
        self.panel_scroll.setObjectName("dashboardPanelScroll")
        self.panel_scroll.setWidgetResizable(True)
        self.panel_scroll.setFrameShape(QFrame.NoFrame)
        self.panel_scroll.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.panel_scroll.viewport().setObjectName("dashboardPanelViewport")
        self.panel_canvas = QWidget()
        self.panel_canvas.setObjectName("dashboardPanelCanvas")
        self.panel_canvas.setAttribute(Qt.WA_StyledBackground, True)
        self.panel_canvas.setMaximumWidth(self._PANEL_CANVAS_MAX_WIDTH)
        self.panel_grid = QGridLayout(self.panel_canvas)
        self.panel_grid.setContentsMargins(0, 0, 0, 0)
        self.panel_grid.setHorizontalSpacing(CFG.SPACING_SM)
        self.panel_grid.setVerticalSpacing(CFG.SPACING_SM)
        self.panel_scroll.setWidget(self.panel_canvas)

        workspace = QWidget()
        workspace.setObjectName("dashboardWorkspace")
        workspace.setAttribute(Qt.WA_StyledBackground, True)
        workspace_layout = QHBoxLayout(workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(CFG.SPACING_SM)
        workspace_layout.addWidget(self._build_dashboard_control_sidebar())
        workspace_layout.addWidget(self.panel_scroll, 1)
        layout.addWidget(workspace, 1)
        self._apply_dashboard_surface_style()

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
        self.kpi_layout = QGridLayout(self.kpi_group)
        self.kpi_layout.setContentsMargins(CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM)
        self.kpi_layout.setHorizontalSpacing(CFG.SPACING_SM)
        self.kpi_layout.setVerticalSpacing(CFG.SPACING_SM)

        self.kpi_tasks = KpiCard("Tasks", "0 / 0", "Done / Total")
        self.kpi_progress = KpiCard("Progress", "0%", "Completion", CFG.COLOR_SUCCESS)
        self.kpi_inflight = KpiCard("In flight", "0", "Active work", CFG.COLOR_ACCENT)
        self.kpi_blocked = KpiCard("Blocked", "0", "Needs action", CFG.COLOR_WARNING)
        self.kpi_critical = KpiCard("Critical", "0", "Path pressure", CFG.COLOR_WARNING)
        self.kpi_late = KpiCard("Late", "0", "Behind plan", CFG.COLOR_DANGER)
        self.kpi_cost = KpiCard("Cost variance", "0.00", "Actual - planned", CFG.COLOR_ACCENT)
        self.kpi_budget = KpiCard("Spend vs plan", "0 / 0", "Actual / planned", CFG.COLOR_SUCCESS)

        self._kpi_cards = [
            self.kpi_tasks,
            self.kpi_progress,
            self.kpi_inflight,
            self.kpi_blocked,
            self.kpi_critical,
            self.kpi_late,
            self.kpi_cost,
            self.kpi_budget,
        ]
        self._sync_kpi_card_layout()

        self.milestone_group = self._build_milestone_panel()
        self.watchlist_group = self._build_watchlist_panel()
        self.register_group = self._build_register_panel()
        self.portfolio_group = self._build_portfolio_panel()
        self.portfolio_group.setTitle("Portfolio Ranking")
        self.evm_group = self._build_evm_panel()
        self.burndown_chart = ChartWidget("Burndown (remaining tasks)")
        self.resource_chart = ChartWidget("Resource load (allocation %)")
        self._prepare_conflicts_dialog()

    def _apply_dashboard_surface_style(self) -> None:
        self.setStyleSheet(
            f"""
            QWidget#dashboardWorkspace,
            QWidget#dashboardPanelCanvas,
            QWidget#dashboardPanelViewport {{
                background-color: {CFG.COLOR_BG_APP};
            }}
            QScrollArea#dashboardPanelScroll {{
                background-color: {CFG.COLOR_BG_APP};
                border: none;
            }}
            """
        )

    def _sync_kpi_card_layout(self) -> None:
        if not hasattr(self, "kpi_layout") or not hasattr(self, "_kpi_cards"):
            return
        width_candidates = [
            self.kpi_group.contentsRect().width(),
            self.kpi_group.width(),
        ]
        if getattr(self, "panel_scroll", None) is not None:
            viewport = self.panel_scroll.viewport()
            width_candidates.extend([viewport.contentsRect().width(), viewport.width()])
        if getattr(self, "panel_canvas", None) is not None:
            width_candidates.extend([self.panel_canvas.contentsRect().width(), self.panel_canvas.width()])

        positive_widths = [width for width in width_candidates if width > 0]
        available_width = min(positive_widths) if positive_widths else (self.width() or 960)
        if available_width <= 380:
            columns = 1
        elif available_width <= 760:
            columns = 2
        elif available_width <= 1100:
            columns = 3
        else:
            columns = 4

        while self.kpi_layout.count():
            item = self.kpi_layout.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                self.kpi_layout.removeWidget(widget)

        for idx, card in enumerate(self._kpi_cards):
            self.kpi_layout.addWidget(card, idx // columns, idx % columns)

        for col in range(4):
            self.kpi_layout.setColumnStretch(col, 1 if col < columns else 0)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._sync_dashboard_panel_visibility()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._schedule_dashboard_layout_sync()

    def _schedule_dashboard_layout_sync(self) -> None:
        if self._layout_sync_scheduled:
            return
        self._layout_sync_scheduled = True
        QTimer.singleShot(0, self._run_scheduled_layout_sync)

    def _run_scheduled_layout_sync(self) -> None:
        self._layout_sync_scheduled = False
        if not self.isVisible():
            return
        self._sync_dashboard_panel_visibility()
        if hasattr(self, "kpi_layout"):
            self.kpi_layout.activate()
        if hasattr(self, "panel_grid"):
            self.panel_grid.activate()
        if hasattr(self, "panel_canvas"):
            self.panel_canvas.updateGeometry()
            self.panel_canvas.adjustSize()
            self.panel_canvas.update()


__all__ = ["DashboardTab"]
