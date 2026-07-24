from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementWorkspaceControllerBase,
)
from src.ui_qml.modules.project_management.presenters import (
    ProjectCollaborationWorkspacePresenter,
    ProjectManagementWorkspacePresenter,
)
from src.ui_qml.shared.models.data_table_model import DynamicTableModel

from . import filter_handler as _fh
from . import mutation_handler as _mut
from . import selection_handler as _sel
from . import state_setters as _setters
from .domain_event_binder import bind_collaboration_domain_events
from .panel_filter_service import CollaborationPanelFilterService
from .refresh_service import refresh_collaboration_workspace
from .state import (
    default_collection,
    default_context,
    default_overview,
    default_selected_item_detail,
)
from .table_models import create_collaboration_table_models

QML_IMPORT_NAME = "ProjectManagement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Project management workspace controllers are provided by the shell runtime.")
class ProjectManagementCollaborationWorkspaceController(
    ProjectManagementWorkspaceControllerBase
):
    overviewChanged = Signal()
    notificationsChanged = Signal()
    selectedProjectIdChanged = Signal()
    selectedTeamIdChanged = Signal()
    selectedPeriodKeyChanged = Signal()
    selectedUnreadKeyChanged = Signal()
    inboxSearchTextChanged = Signal()
    mentionsSearchTextChanged = Signal()
    approvalsSearchTextChanged = Signal()
    teamUpdatesSearchTextChanged = Signal()
    inboxChanged = Signal()
    recentActivityChanged = Signal()
    activePresenceChanged = Signal()
    contextChanged = Signal()
    panelTabsChanged = Signal()
    mentionsChanged = Signal()
    approvalsChanged = Signal()
    activityFeedChanged = Signal()
    teamUpdatesChanged = Signal()
    selectedItemDetailChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: ProjectManagementWorkspacePresenter | None = None,
        collaboration_workspace_presenter: ProjectCollaborationWorkspacePresenter
        | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = workspace_presenter or ProjectManagementWorkspacePresenter(
            "project_management.collaboration"
        )
        self._collaboration_workspace_presenter = (
            collaboration_workspace_presenter
            or ProjectCollaborationWorkspacePresenter()
        )
        self._table_models = create_collaboration_table_models(self)
        self._filter_service = CollaborationPanelFilterService()
        self._overview: dict[str, object] = default_overview()
        self._notifications: dict[str, object] = default_collection()
        self._inbox: dict[str, object] = default_collection()
        self._recent_activity: dict[str, object] = default_collection()
        self._active_presence: dict[str, object] = default_collection()
        self._context: dict[str, object] = default_context()
        self._panel_tabs: list[dict[str, object]] = []
        self._mentions: dict[str, object] = default_collection()
        self._approvals: dict[str, object] = default_collection()
        self._activity_feed: dict[str, object] = default_collection()
        self._team_updates: dict[str, object] = default_collection()
        self._selected_item_detail: dict[str, object] = default_selected_item_detail()
        self._panel_item_index: dict[str, dict[str, dict[str, object]]] = {}
        bind_collaboration_domain_events(self)
        self.refresh()

    # ── Overview / notifications ──────────────────────────────────────

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._overview

    @Property("QVariantMap", notify=notificationsChanged)
    def notifications(self) -> dict[str, object]:
        return self._notifications

    # ── Panel table models ────────────────────────────────────────────

    @Property(QObject, constant=True)
    def inboxTableModel(self) -> DynamicTableModel:
        return self._table_models.inbox

    @Property(QObject, constant=True)
    def mentionsTableModel(self) -> DynamicTableModel:
        return self._table_models.mentions

    @Property(QObject, constant=True)
    def approvalsTableModel(self) -> DynamicTableModel:
        return self._table_models.approvals

    @Property(QObject, constant=True)
    def teamUpdatesTableModel(self) -> DynamicTableModel:
        return self._table_models.team_updates

    @Property(QObject, constant=True)
    def relatedItemsTableModel(self) -> DynamicTableModel:
        return self._table_models.related_items

    # ── Filter and search state ───────────────────────────────────────

    @Property(str, notify=selectedProjectIdChanged)
    def selectedProjectId(self) -> str:
        return self._filter_service.selected_project_id

    @Property(str, notify=selectedTeamIdChanged)
    def selectedTeamId(self) -> str:
        return self._filter_service.selected_team_id

    @Property(str, notify=selectedPeriodKeyChanged)
    def selectedPeriodKey(self) -> str:
        return self._filter_service.selected_period_key

    @Property(str, notify=selectedUnreadKeyChanged)
    def selectedUnreadKey(self) -> str:
        return self._filter_service.selected_unread_key

    @Property(str, notify=inboxSearchTextChanged)
    def inboxSearchText(self) -> str:
        return self._filter_service.inbox_search_text

    @Property(str, notify=mentionsSearchTextChanged)
    def mentionsSearchText(self) -> str:
        return self._filter_service.mentions_search_text

    @Property(str, notify=approvalsSearchTextChanged)
    def approvalsSearchText(self) -> str:
        return self._filter_service.approvals_search_text

    @Property(str, notify=teamUpdatesSearchTextChanged)
    def teamUpdatesSearchText(self) -> str:
        return self._filter_service.team_updates_search_text

    # ── Collection properties ─────────────────────────────────────────

    @Property("QVariantMap", notify=inboxChanged)
    def inbox(self) -> dict[str, object]:
        return self._inbox

    @Property("QVariantMap", notify=recentActivityChanged)
    def recentActivity(self) -> dict[str, object]:
        return self._recent_activity

    @Property("QVariantMap", notify=activePresenceChanged)
    def activePresence(self) -> dict[str, object]:
        return self._active_presence

    @Property("QVariantMap", notify=contextChanged)
    def context(self) -> dict[str, object]:
        return self._context

    @Property("QVariantList", notify=panelTabsChanged)
    def panelTabs(self) -> list[dict[str, object]]:
        return self._panel_tabs

    @Property("QVariantMap", notify=mentionsChanged)
    def mentions(self) -> dict[str, object]:
        return self._mentions

    @Property("QVariantMap", notify=approvalsChanged)
    def approvals(self) -> dict[str, object]:
        return self._approvals

    @Property("QVariantMap", notify=activityFeedChanged)
    def activityFeed(self) -> dict[str, object]:
        return self._activity_feed

    @Property("QVariantMap", notify=teamUpdatesChanged)
    def teamUpdates(self) -> dict[str, object]:
        return self._team_updates

    @Property("QVariantMap", notify=selectedItemDetailChanged)
    def selectedItemDetail(self) -> dict[str, object]:
        return self._selected_item_detail

    # ── Refresh ───────────────────────────────────────────────────────

    @Slot()
    def refresh(self) -> None:
        refresh_collaboration_workspace(self)

    # ── Filter slots ──────────────────────────────────────────────────

    @Slot(str)
    def setSelectedProjectId(self, value: str) -> None:
        _fh.set_selected_project_id(self, value)

    @Slot(str)
    def setSelectedTeamId(self, value: str) -> None:
        _fh.set_selected_team_id(self, value)

    @Slot(str)
    def setSelectedPeriodKey(self, value: str) -> None:
        _fh.set_selected_period_key(self, value)

    @Slot(str)
    def setSelectedUnreadKey(self, value: str) -> None:
        _fh.set_selected_unread_key(self, value)

    @Slot(str)
    def setInboxSearchText(self, text: str) -> None:
        _fh.set_inbox_search_text(self, text)

    @Slot(str)
    def setMentionsSearchText(self, text: str) -> None:
        _fh.set_mentions_search_text(self, text)

    @Slot(str)
    def setApprovalsSearchText(self, text: str) -> None:
        _fh.set_approvals_search_text(self, text)

    @Slot(str)
    def setTeamUpdatesSearchText(self, text: str) -> None:
        _fh.set_team_updates_search_text(self, text)

    # ── Selection slots ───────────────────────────────────────────────

    @Slot(str, str)
    def selectItem(self, panel_id: str, item_id: str) -> None:
        _sel.select_item(self, panel_id, item_id)

    @Slot()
    def clearSelection(self) -> None:
        _sel.clear_selection(self)

    @Slot(str, str, result=str)
    def routeForItem(self, panel_id: str, item_id: str) -> str:
        return _sel.route_for_item(self, panel_id, item_id)

    # ── Mutation slots ────────────────────────────────────────────────

    @Slot(str, result="QVariantMap")
    def markTaskRead(self, task_id: str) -> dict[str, object]:
        return _mut.mark_task_read(self, task_id)

    @Slot(str, str, result="QVariantMap")
    def markItemRead(self, panel_id: str, item_id: str) -> dict[str, object]:
        return _mut.mark_item_read(self, panel_id, item_id)

    @Slot(str, result="QVariantMap")
    def approveRequest(self, request_id: str) -> dict[str, object]:
        return _mut.approve_request(self, request_id)

    @Slot(str, result="QVariantMap")
    def rejectRequest(self, request_id: str) -> dict[str, object]:
        return _mut.reject_request(self, request_id)

    @Slot(str, result="QVariantMap")
    def exportPanel(self, panel_id: str) -> dict[str, object]:
        return _mut.export_panel(self, panel_id)

    # ── Domain event handler ──────────────────────────────────────────

    def _on_domain_event(self, _payload: object) -> None:
        self._request_domain_refresh()

    # ── State setters ─────────────────────────────────────────────────

    def _set_overview(self, overview: dict[str, object]) -> None:
        _setters.set_overview(self, overview)

    def _set_notifications(self, notifications: dict[str, object]) -> None:
        _setters.set_notifications(self, notifications)

    def _set_inbox(self, inbox: dict[str, object]) -> None:
        _setters.set_inbox(self, inbox)

    def _set_recent_activity(self, recent_activity: dict[str, object]) -> None:
        _setters.set_recent_activity(self, recent_activity)

    def _set_active_presence(self, active_presence: dict[str, object]) -> None:
        _setters.set_active_presence(self, active_presence)

    def _set_context(self, context: dict[str, object]) -> None:
        _setters.set_context(self, context)

    def _set_panel_tabs(self, panel_tabs: list[dict[str, object]]) -> None:
        _setters.set_panel_tabs(self, panel_tabs)

    def _set_mentions(self, mentions: dict[str, object]) -> None:
        _setters.set_mentions(self, mentions)

    def _set_approvals(self, approvals: dict[str, object]) -> None:
        _setters.set_approvals(self, approvals)

    def _set_activity_feed(self, activity_feed: dict[str, object]) -> None:
        _setters.set_activity_feed(self, activity_feed)

    def _set_team_updates(self, team_updates: dict[str, object]) -> None:
        _setters.set_team_updates(self, team_updates)

    def _set_selected_item_detail(
        self, selected_item_detail: dict[str, object]
    ) -> None:
        _setters.set_selected_item_detail(self, selected_item_detail)


__all__ = ["ProjectManagementCollaborationWorkspaceController"]
