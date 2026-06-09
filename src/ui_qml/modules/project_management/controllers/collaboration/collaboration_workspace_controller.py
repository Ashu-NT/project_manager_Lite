from __future__ import annotations

import logging

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementWorkspaceControllerBase,
    run_mutation,
    serialize_collaboration_collection_view_model,
    serialize_collaboration_context_view_model,
    serialize_collaboration_detail_view_model,
    serialize_collaboration_overview_view_model,
    serialize_collaboration_panel_tab_view_models,
    serialize_workspace_view_model,
)
from src.ui_qml.modules.project_management.presenters import (
    ProjectCollaborationWorkspacePresenter,
    ProjectManagementWorkspacePresenter,
)
from src.ui_qml.modules.project_management.view_models.collaboration import (
    CollaborationDetailViewModel,
)
from src.ui_qml.shared.models.data_table_model import DynamicTableModel

from .detail_builder import build_detail_payload
from .domain_event_binder import bind_collaboration_domain_events
from .panel_filter_service import CollaborationPanelFilterService
from .panel_row_builder import (
    build_approvals_rows,
    build_inbox_rows,
    build_mentions_rows,
    build_team_updates_rows,
)
from .state import (
    default_collection,
    default_context,
    default_overview,
    default_selected_item_detail,
)
from .table_models import create_collaboration_table_models
from .utils import panel_label

QML_IMPORT_NAME = "ProjectManagement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1

logger = logging.getLogger(__name__)


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
    auditFeedChanged = Signal()
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
        self._audit_feed: dict[str, object] = default_collection()
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

    @Slot(str)
    def setSelectedProjectId(self, value: str) -> None:
        v = (value or "").strip() or "all"
        if v == self._filter_service.selected_project_id:
            return
        self._filter_service.selected_project_id = v
        self.selectedProjectIdChanged.emit()
        self._rebuild_all_panel_models()

    @Slot(str)
    def setSelectedTeamId(self, value: str) -> None:
        v = (value or "").strip() or "all"
        if v == self._filter_service.selected_team_id:
            return
        self._filter_service.selected_team_id = v
        self.selectedTeamIdChanged.emit()
        self._rebuild_all_panel_models()

    @Slot(str)
    def setSelectedPeriodKey(self, value: str) -> None:
        v = (value or "").strip() or "all"
        if v == self._filter_service.selected_period_key:
            return
        self._filter_service.selected_period_key = v
        self.selectedPeriodKeyChanged.emit()
        self._rebuild_all_panel_models()

    @Slot(str)
    def setSelectedUnreadKey(self, value: str) -> None:
        v = (value or "").strip() or "all"
        if v == self._filter_service.selected_unread_key:
            return
        self._filter_service.selected_unread_key = v
        self.selectedUnreadKeyChanged.emit()
        self._rebuild_all_panel_models()

    @Slot(str)
    def setInboxSearchText(self, text: str) -> None:
        v = (text or "").strip()
        if v == self._filter_service.inbox_search_text:
            return
        self._filter_service.inbox_search_text = v
        self.inboxSearchTextChanged.emit()
        self._table_models.inbox.set_rows(
            build_inbox_rows(self._notifications, self._filter_service)
        )

    @Slot(str)
    def setMentionsSearchText(self, text: str) -> None:
        v = (text or "").strip()
        if v == self._filter_service.mentions_search_text:
            return
        self._filter_service.mentions_search_text = v
        self.mentionsSearchTextChanged.emit()
        self._table_models.mentions.set_rows(
            build_mentions_rows(self._mentions, self._filter_service)
        )

    @Slot(str)
    def setApprovalsSearchText(self, text: str) -> None:
        v = (text or "").strip()
        if v == self._filter_service.approvals_search_text:
            return
        self._filter_service.approvals_search_text = v
        self.approvalsSearchTextChanged.emit()
        self._table_models.approvals.set_rows(
            build_approvals_rows(self._approvals, self._filter_service)
        )

    @Slot(str)
    def setTeamUpdatesSearchText(self, text: str) -> None:
        v = (text or "").strip()
        if v == self._filter_service.team_updates_search_text:
            return
        self._filter_service.team_updates_search_text = v
        self.teamUpdatesSearchTextChanged.emit()
        self._table_models.team_updates.set_rows(
            build_team_updates_rows(self._team_updates, self._filter_service)
        )

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

    @Property("QVariantMap", notify=auditFeedChanged)
    def auditFeed(self) -> dict[str, object]:
        return self._audit_feed

    @Property("QVariantMap", notify=selectedItemDetailChanged)
    def selectedItemDetail(self) -> dict[str, object]:
        return self._selected_item_detail

    # ── Slots ─────────────────────────────────────────────────────────

    @Slot()
    def refresh(self) -> None:
        self._set_is_loading(True)
        try:
            self._set_error_message("")
            self._set_feedback_message("")
            self._set_workspace(
                serialize_workspace_view_model(
                    self._workspace_presenter.build_view_model()
                )
            )
            ws = self._collaboration_workspace_presenter.build_workspace_state()
            self._set_overview(serialize_collaboration_overview_view_model(ws.overview))
            self._set_notifications(
                serialize_collaboration_collection_view_model(ws.notifications)
            )
            self._set_inbox(serialize_collaboration_collection_view_model(ws.inbox))
            self._set_recent_activity(
                serialize_collaboration_collection_view_model(ws.recent_activity)
            )
            self._set_active_presence(
                serialize_collaboration_collection_view_model(ws.active_presence)
            )
            self._set_context(serialize_collaboration_context_view_model(ws.context))
            self._set_panel_tabs(
                serialize_collaboration_panel_tab_view_models(ws.panel_tabs)
            )
            self._set_mentions(serialize_collaboration_collection_view_model(ws.mentions))
            self._set_approvals(
                serialize_collaboration_collection_view_model(ws.approvals)
            )
            self._set_activity_feed(
                serialize_collaboration_collection_view_model(ws.activity_feed)
            )
            self._set_team_updates(
                serialize_collaboration_collection_view_model(ws.team_updates)
            )
            self._set_audit_feed(
                serialize_collaboration_collection_view_model(ws.audit_feed)
            )
            self._rebuild_panel_item_index()
            self._set_empty_state(ws.empty_state)
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.exception("Failed to refresh project management collaboration workspace.")
            self._set_error_message(str(exc))
        finally:
            self._set_is_loading(False)

    @Slot(str, result="QVariantMap")
    def markTaskRead(self, task_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._collaboration_workspace_presenter.mark_task_mentions_read(
                task_id
            ),
            success_message="Task mentions marked as read.",
            on_success=self._request_domain_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, str, result="QVariantMap")
    def markItemRead(self, panel_id: str, item_id: str) -> dict[str, object]:
        item = self._item_for_panel(panel_id, item_id)
        task_id = str(item.get("state", {}).get("taskId") or "").strip() if item else ""
        if not task_id:
            return {
                "ok": False,
                "message": "The selected collaboration item is not linked to a task mention.",
            }
        return self.markTaskRead(task_id)

    @Slot(str, result="QVariantMap")
    def approveRequest(self, request_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._collaboration_workspace_presenter.approve_request(
                request_id
            ),
            success_message="Approval request approved.",
            on_success=self._request_domain_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def rejectRequest(self, request_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._collaboration_workspace_presenter.reject_request(
                request_id
            ),
            success_message="Approval request rejected.",
            on_success=self._request_domain_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def exportPanel(self, panel_id: str) -> dict[str, object]:
        label = panel_label(str(panel_id or ""))
        message = (
            f"Export is not available here. Open the Reports section to generate "
            f"{label.lower()} summaries and collaboration exports."
        )
        self._set_error_message("")
        self._set_feedback_message(message)
        return {"ok": True, "message": message}

    @Slot(str, str)
    def selectItem(self, panel_id: str, item_id: str) -> None:
        item = self._item_for_panel(panel_id, item_id)
        if item is None:
            self._set_selected_item_detail(
                serialize_collaboration_detail_view_model(
                    CollaborationDetailViewModel(
                        id="", title="", status_label="", subtitle="", description=""
                    )
                )
            )
            return
        self._set_selected_item_detail(
            build_detail_payload(panel_id, item, self._panel_item_index)
        )

    @Slot()
    def clearSelection(self) -> None:
        self._set_selected_item_detail(
            serialize_collaboration_detail_view_model(
                CollaborationDetailViewModel(
                    id="", title="", status_label="", subtitle="", description=""
                )
            )
        )

    @Slot(str, str, result=str)
    def routeForItem(self, panel_id: str, item_id: str) -> str:
        item = self._item_for_panel(panel_id, item_id)
        if item is None:
            return ""
        return str(item.get("state", {}).get("routeId") or "")

    # ── Domain event handler ──────────────────────────────────────────

    def _on_domain_event(self, _payload: object) -> None:
        self._request_domain_refresh()

    # ── Internal state management ─────────────────────────────────────

    def _rebuild_panel_item_index(self) -> None:
        self._panel_item_index = {}
        panel_map = {
            "inbox": self._notifications,
            "mentions": self._mentions,
            "approvals": self._approvals,
            "activity": self._activity_feed,
            "team_updates": self._team_updates,
            "audit": self._audit_feed,
        }
        for pid, panel in panel_map.items():
            self._panel_item_index[pid] = {
                str(item.get("id") or ""): dict(item)
                for item in panel.get("items", [])
            }

    def _item_for_panel(self, panel_id: str, item_id: str) -> dict[str, object] | None:
        return self._panel_item_index.get(str(panel_id or ""), {}).get(
            str(item_id or "")
        )

    def _rebuild_all_panel_models(self) -> None:
        self._table_models.inbox.set_rows(
            build_inbox_rows(self._notifications, self._filter_service)
        )
        self._table_models.mentions.set_rows(
            build_mentions_rows(self._mentions, self._filter_service)
        )
        self._table_models.approvals.set_rows(
            build_approvals_rows(self._approvals, self._filter_service)
        )
        self._table_models.team_updates.set_rows(
            build_team_updates_rows(self._team_updates, self._filter_service)
        )

    def _set_overview(self, overview: dict[str, object]) -> None:
        if overview == self._overview:
            return
        self._overview = overview
        self.overviewChanged.emit()

    def _set_notifications(self, notifications: dict[str, object]) -> None:
        if notifications == self._notifications:
            return
        self._notifications = notifications
        self._table_models.inbox.set_rows(
            build_inbox_rows(self._notifications, self._filter_service)
        )
        self.notificationsChanged.emit()

    def _set_inbox(self, inbox: dict[str, object]) -> None:
        if inbox == self._inbox:
            return
        self._inbox = inbox
        self.inboxChanged.emit()

    def _set_recent_activity(self, recent_activity: dict[str, object]) -> None:
        if recent_activity == self._recent_activity:
            return
        self._recent_activity = recent_activity
        self.recentActivityChanged.emit()

    def _set_active_presence(self, active_presence: dict[str, object]) -> None:
        if active_presence == self._active_presence:
            return
        self._active_presence = active_presence
        self.activePresenceChanged.emit()

    def _set_context(self, context: dict[str, object]) -> None:
        if context == self._context:
            return
        self._context = context
        self.contextChanged.emit()

    def _set_panel_tabs(self, panel_tabs: list[dict[str, object]]) -> None:
        if panel_tabs == self._panel_tabs:
            return
        self._panel_tabs = panel_tabs
        self.panelTabsChanged.emit()

    def _set_mentions(self, mentions: dict[str, object]) -> None:
        if mentions == self._mentions:
            return
        self._mentions = mentions
        self._table_models.mentions.set_rows(
            build_mentions_rows(self._mentions, self._filter_service)
        )
        self.mentionsChanged.emit()

    def _set_approvals(self, approvals: dict[str, object]) -> None:
        if approvals == self._approvals:
            return
        self._approvals = approvals
        self._table_models.approvals.set_rows(
            build_approvals_rows(self._approvals, self._filter_service)
        )
        self.approvalsChanged.emit()

    def _set_activity_feed(self, activity_feed: dict[str, object]) -> None:
        if activity_feed == self._activity_feed:
            return
        self._activity_feed = activity_feed
        self.activityFeedChanged.emit()

    def _set_team_updates(self, team_updates: dict[str, object]) -> None:
        if team_updates == self._team_updates:
            return
        self._team_updates = team_updates
        self._table_models.team_updates.set_rows(
            build_team_updates_rows(self._team_updates, self._filter_service)
        )
        self.teamUpdatesChanged.emit()

    def _set_audit_feed(self, audit_feed: dict[str, object]) -> None:
        if audit_feed == self._audit_feed:
            return
        self._audit_feed = audit_feed
        self.auditFeedChanged.emit()

    def _set_selected_item_detail(self, selected_item_detail: dict[str, object]) -> None:
        if selected_item_detail == self._selected_item_detail:
            return
        self._selected_item_detail = selected_item_detail
        related = (
            selected_item_detail.get("relatedItems")
            if isinstance(selected_item_detail, dict)
            else {}
        )
        self._table_models.related_items.set_rows(
            related.get("items", []) if isinstance(related, dict) else []
        )
        self.selectedItemDetailChanged.emit()


__all__ = ["ProjectManagementCollaborationWorkspaceController"]
