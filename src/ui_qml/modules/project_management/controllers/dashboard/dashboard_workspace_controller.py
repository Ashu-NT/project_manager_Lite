from __future__ import annotations

import logging

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementWorkspaceControllerBase,
    serialize_workspace_view_model,
)
from src.ui_qml.modules.project_management.controllers.dashboard.dashboard_operational_table_mixin import (
    DashboardOperationalTableMixin,
)
from src.ui_qml.modules.project_management.controllers.dashboard.dashboard_refresh_mixin import (
    DashboardRefreshMixin,
)
from src.ui_qml.modules.project_management.controllers.dashboard.dashboard_selection_mixin import (
    DashboardSelectionMixin,
)
from src.ui_qml.modules.project_management.controllers.dashboard.dashboard_state_mixin import (
    DashboardStateMixin,
)
from src.ui_qml.modules.project_management.controllers.dashboard.dashboard_types import (
    DashboardMap,
    DashboardObjectList,
    DashboardOptionList,
    default_activity_feed,
    default_dashboard_overview,
)
from src.ui_qml.modules.project_management.presenters import (
    ProjectDashboardWorkspacePresenter,
    ProjectManagementWorkspacePresenter,
)
from src.ui_qml.shared.models.data_table_model import DynamicTableModel

QML_IMPORT_NAME = "ProjectManagement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1

logger = logging.getLogger(__name__)


@QmlElement
@QmlUncreatable("Project management workspace controllers are provided by the shell runtime.")
class ProjectManagementDashboardWorkspaceController(
    DashboardRefreshMixin,
    DashboardSelectionMixin,
    DashboardOperationalTableMixin,
    DashboardStateMixin,
    ProjectManagementWorkspaceControllerBase,
):
    overviewChanged = Signal()
    hasLoadedChanged = Signal()
    projectOptionsChanged = Signal()
    selectedProjectIdChanged = Signal()
    baselineOptionsChanged = Signal()
    selectedBaselineIdChanged = Signal()
    periodOptionsChanged = Signal()
    selectedPeriodKeyChanged = Signal()
    viewOptionsChanged = Signal()
    selectedViewKeyChanged = Signal()
    healthCardsChanged = Signal()
    operationalTabsChanged = Signal()
    selectedOperationalTabIdChanged = Signal()
    operationalTableChanged = Signal()
    operationalSearchTextChanged = Signal()
    operationalPageChanged = Signal()
    operationalPageSizeChanged = Signal()
    operationalTotalCountChanged = Signal()
    selectedOperationalRowIdChanged = Signal()
    activityFeedChanged = Signal()
    panelsChanged = Signal()
    chartsChanged = Signal()
    sectionsChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: ProjectManagementWorkspacePresenter | None = None,
        dashboard_workspace_presenter: ProjectDashboardWorkspacePresenter | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = workspace_presenter or ProjectManagementWorkspacePresenter(
            "project_management.dashboard"
        )
        self._dashboard_workspace_presenter = (
            dashboard_workspace_presenter or ProjectDashboardWorkspacePresenter()
        )
        workspace_view_model = serialize_workspace_view_model(
            self._workspace_presenter.build_view_model()
        )
        self._workspace = workspace_view_model
        self._overview = default_dashboard_overview(
            str(workspace_view_model.get("title", "") or "Dashboard")
        )
        self._has_loaded = False
        self._is_refreshing = False
        self._load_count = 0
        self._refresh_count = 0
        self._selector_debug_counts: dict[str, int] = {}
        self._project_options: DashboardOptionList = []
        self._selected_project_id = ""
        self._baseline_options: DashboardOptionList = []
        self._selected_baseline_id = ""
        self._period_options: DashboardOptionList = []
        self._selected_period_key = ""
        self._view_options: DashboardOptionList = []
        self._selected_view_key = ""
        self._health_cards: DashboardObjectList = []
        self._operational_tabs: DashboardObjectList = []
        self._selected_operational_tab_id = ""
        self._operational_table_model = DynamicTableModel(self)
        self._operational_table = self._empty_operational_table()
        self._operational_search_text = ""
        self._operational_page = 1
        self._operational_page_size = 25
        self._operational_total_count = 0
        self._selected_operational_row_id = ""
        self._activity_feed = default_activity_feed()
        self._panels: DashboardObjectList = []
        self._charts: DashboardObjectList = []
        self._sections: DashboardObjectList = []
        self._raw_operational_tables: DashboardObjectList = []
        self._bind_domain_events()

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> DashboardMap: return self._overview

    @Property(bool, notify=hasLoadedChanged)
    def hasLoaded(self) -> bool: return self._has_loaded

    @Property("QVariantList", notify=projectOptionsChanged)
    def projectOptions(self) -> DashboardOptionList: return self._project_options

    @Property(str, notify=selectedProjectIdChanged)
    def selectedProjectId(self) -> str: return self._selected_project_id

    @Property("QVariantList", notify=baselineOptionsChanged)
    def baselineOptions(self) -> DashboardOptionList: return self._baseline_options

    @Property(str, notify=selectedBaselineIdChanged)
    def selectedBaselineId(self) -> str: return self._selected_baseline_id

    @Property("QVariantList", notify=periodOptionsChanged)
    def periodOptions(self) -> DashboardOptionList: return self._period_options

    @Property(str, notify=selectedPeriodKeyChanged)
    def selectedPeriodKey(self) -> str: return self._selected_period_key

    @Property("QVariantList", notify=viewOptionsChanged)
    def viewOptions(self) -> DashboardOptionList: return self._view_options

    @Property(str, notify=selectedViewKeyChanged)
    def selectedViewKey(self) -> str: return self._selected_view_key

    @Property("QVariantList", notify=healthCardsChanged)
    def healthCards(self) -> DashboardObjectList: return self._health_cards

    @Property("QVariantList", notify=operationalTabsChanged)
    def operationalTabs(self) -> DashboardObjectList: return self._operational_tabs

    @Property(str, notify=selectedOperationalTabIdChanged)
    def selectedOperationalTabId(self) -> str: return self._selected_operational_tab_id

    @Property("QVariantMap", notify=operationalTableChanged)
    def operationalTable(self) -> DashboardMap: return self._operational_table

    @Property(QObject, constant=True)
    def operationalTableModel(self) -> DynamicTableModel: return self._operational_table_model

    @Property(str, notify=operationalSearchTextChanged)
    def operationalSearchText(self) -> str: return self._operational_search_text

    @Property(int, notify=operationalPageChanged)
    def operationalPage(self) -> int: return self._operational_page

    @Property(int, notify=operationalPageSizeChanged)
    def operationalPageSize(self) -> int: return self._operational_page_size

    @Property(int, notify=operationalTotalCountChanged)
    def operationalTotalCount(self) -> int: return self._operational_total_count

    @Property(str, notify=selectedOperationalRowIdChanged)
    def selectedOperationalRowId(self) -> str: return self._selected_operational_row_id

    @Property("QVariantMap", notify=activityFeedChanged)
    def activityFeed(self) -> DashboardMap: return self._activity_feed

    @Property("QVariantList", notify=panelsChanged)
    def panels(self) -> DashboardObjectList: return self._panels

    @Property("QVariantList", notify=chartsChanged)
    def charts(self) -> DashboardObjectList: return self._charts

    @Property("QVariantList", notify=sectionsChanged)
    def sections(self) -> DashboardObjectList: return self._sections

    @Slot()
    def load(self) -> None: self._load_dashboard()

    @Slot()
    def refresh(self) -> None: self._refresh_dashboard_from_qml()

    @Slot(str)
    def selectProject(self, project_id: str) -> None: self._select_project_from_qml(project_id)

    @Slot(str)
    def selectBaseline(self, baseline_id: str) -> None: self._select_baseline_from_qml(baseline_id)

    @Slot(str)
    def selectPeriod(self, period_key: str) -> None: self._select_period_from_qml(period_key)

    @Slot(str)
    def selectView(self, view_key: str) -> None: self._select_view_from_qml(view_key)

    @Slot(str)
    def selectOperationalTab(self, tab_id: str) -> None: self._select_operational_tab_from_qml(tab_id)

    @Slot(str)
    def setOperationalSearchText(self, search_text: str) -> None: self._set_operational_search_text_from_qml(search_text)

    @Slot(int)
    def setOperationalPage(self, page: int) -> None: self._set_operational_page_from_qml(page)

    @Slot(int)
    def setOperationalPageSize(self, page_size: int) -> None: self._set_operational_page_size_from_qml(page_size)

    @Slot(str)
    def selectOperationalRow(self, row_id: str) -> None: self._select_operational_row_from_qml(row_id)

    @Slot(result="QVariantMap")
    def exportDashboard(self) -> DashboardMap:
        message = "Export is not available here. Open the Reports section to generate dashboard summaries and project health exports."
        self._set_error_message("")
        self._set_feedback_message(message)
        return {"ok": True, "message": message}


__all__ = ["ProjectManagementDashboardWorkspaceController"]
