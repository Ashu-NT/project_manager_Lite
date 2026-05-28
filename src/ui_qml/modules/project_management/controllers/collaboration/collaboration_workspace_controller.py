from __future__ import annotations

import logging

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.core.platform.notifications.domain_events import domain_events
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
    CollaborationCollectionViewModel,
    CollaborationDetailFieldViewModel,
    CollaborationDetailViewModel,
    CollaborationRecordViewModel,
)

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
        self._overview: dict[str, object] = {"title": "", "subtitle": "", "metrics": []}
        self._notifications: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._inbox: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._recent_activity: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._active_presence: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._context: dict[str, object] = {
            "projectOptions": [],
            "teamOptions": [],
            "periodOptions": [],
            "unreadOptions": [],
        }
        self._panel_tabs: list[dict[str, object]] = []
        self._mentions: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._approvals: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._activity_feed: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._team_updates: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._audit_feed: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._selected_item_detail: dict[str, object] = {
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "state": {},
            "fields": [],
            "activity": {"title": "", "subtitle": "", "emptyState": "", "items": []},
            "relatedItems": {
                "title": "",
                "subtitle": "",
                "emptyState": "",
                "items": [],
            },
            "audit": {"title": "", "subtitle": "", "emptyState": "", "items": []},
        }
        self._panel_item_index: dict[str, dict[str, dict[str, object]]] = {}
        self._bind_domain_events()
        self.refresh()

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._overview

    @Property("QVariantMap", notify=notificationsChanged)
    def notifications(self) -> dict[str, object]:
        return self._notifications

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
            workspace_state = self._collaboration_workspace_presenter.build_workspace_state()
            self._set_overview(
                serialize_collaboration_overview_view_model(workspace_state.overview)
            )
            self._set_notifications(
                serialize_collaboration_collection_view_model(
                    workspace_state.notifications
                )
            )
            self._set_inbox(
                serialize_collaboration_collection_view_model(workspace_state.inbox)
            )
            self._set_recent_activity(
                serialize_collaboration_collection_view_model(
                    workspace_state.recent_activity
                )
            )
            self._set_active_presence(
                serialize_collaboration_collection_view_model(
                    workspace_state.active_presence
                )
            )
            self._set_context(
                serialize_collaboration_context_view_model(workspace_state.context)
            )
            self._set_panel_tabs(
                serialize_collaboration_panel_tab_view_models(workspace_state.panel_tabs)
            )
            self._set_mentions(
                serialize_collaboration_collection_view_model(workspace_state.mentions)
            )
            self._set_approvals(
                serialize_collaboration_collection_view_model(workspace_state.approvals)
            )
            self._set_activity_feed(
                serialize_collaboration_collection_view_model(
                    workspace_state.activity_feed
                )
            )
            self._set_team_updates(
                serialize_collaboration_collection_view_model(
                    workspace_state.team_updates
                )
            )
            self._set_audit_feed(
                serialize_collaboration_collection_view_model(workspace_state.audit_feed)
            )
            self._rebuild_panel_item_index()
            self._set_empty_state(workspace_state.empty_state)
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
        panel_label = self._panel_label(str(panel_id or ""))
        message = f"Export is not available here. Open the Reports section to generate {panel_label.lower()} summaries and collaboration exports."
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
                        id="",
                        title="",
                        status_label="",
                        subtitle="",
                        description="",
                    )
                )
            )
            return
        self._set_selected_item_detail(self._build_detail_payload(panel_id, item))

    @Slot()
    def clearSelection(self) -> None:
        self._set_selected_item_detail(
            serialize_collaboration_detail_view_model(
                CollaborationDetailViewModel(
                    id="",
                    title="",
                    status_label="",
                    subtitle="",
                    description="",
                )
            )
        )

    @Slot(str, str, result=str)
    def routeForItem(self, panel_id: str, item_id: str) -> str:
        item = self._item_for_panel(panel_id, item_id)
        if item is None:
            return ""
        return str(item.get("state", {}).get("routeId") or "")

    def _bind_domain_events(self) -> None:
        self._subscribe_domain_change(
            "project",
            "project_tasks",
            "task_collaboration",
            scope_code="project_management",
        )
        self._subscribe_domain_signal(
            domain_events.approvals_changed,
            self._on_domain_event,
        )
        self._subscribe_domain_signal(
            domain_events.timesheet_periods_changed,
            self._on_domain_event,
        )

    def _on_domain_event(self, _payload: object) -> None:
        self._request_domain_refresh()

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
        for panel_id, panel in panel_map.items():
            self._panel_item_index[panel_id] = {
                str(item.get("id") or ""): dict(item)
                for item in panel.get("items", [])
            }

    def _item_for_panel(self, panel_id: str, item_id: str) -> dict[str, object] | None:
        return self._panel_item_index.get(str(panel_id or ""), {}).get(
            str(item_id or "")
        )

    def _build_detail_payload(
        self,
        panel_id: str,
        item: dict[str, object],
    ) -> dict[str, object]:
        state = dict(item.get("state") or {})
        project_id = str(state.get("projectId") or "")
        task_id = str(state.get("taskId") or "")
        item_id = str(item.get("id") or "")
        related = []
        route_id = str(state.get("routeId") or "")
        if route_id:
            related.append(
                {
                    "id": f"{item_id}:source",
                    "title": "Open Source Workspace",
                    "statusLabel": "Navigation",
                    "subtitle": route_id.replace(".", " / "),
                    "supportingText": str(item.get("subtitle") or ""),
                    "metaText": str(item.get("metaText") or ""),
                    "state": {"routeId": route_id},
                }
            )
        if task_id:
            related.append(
                {
                    "id": f"{item_id}:task",
                    "title": "Related Task",
                    "statusLabel": "Task",
                    "subtitle": task_id,
                    "supportingText": str(item.get("title") or ""),
                    "metaText": "",
                    "state": {"routeId": "project_management.tasks", "taskId": task_id},
                }
            )
        if project_id:
            related.append(
                {
                    "id": f"{item_id}:project",
                    "title": "Related Project",
                    "statusLabel": "Project",
                    "subtitle": project_id,
                    "supportingText": str(state.get("projectName") or ""),
                    "metaText": "",
                    "state": {"routeId": "project_management.projects", "projectId": project_id},
                }
            )

        activity_items = self._matching_items_for_task_or_project(
            source_panels=("activity", "team_updates"),
            task_id=task_id,
            project_id=project_id,
            exclude_item_id=item_id,
        )
        audit_items = self._matching_items_for_task_or_project(
            source_panels=("audit", "inbox", "mentions", "approvals"),
            task_id=task_id,
            project_id=project_id,
            exclude_item_id=item_id,
        )
        detail = CollaborationDetailViewModel(
            id=item_id,
            title=str(item.get("title") or ""),
            status_label=str(item.get("statusLabel") or ""),
            subtitle=str(item.get("subtitle") or ""),
            description=str(item.get("supportingText") or ""),
            state={
                "panelId": panel_id,
                "routeId": route_id,
                **state,
            },
            fields=(
                CollaborationDetailFieldViewModel("Panel", self._panel_label(panel_id)),
                CollaborationDetailFieldViewModel(
                    "Project",
                    str(state.get("projectName") or state.get("projectId") or "Cross-project"),
                ),
                CollaborationDetailFieldViewModel(
                    "Actor",
                    str(
                        state.get("actorUsername")
                        or state.get("requestor")
                        or state.get("username")
                        or "System"
                    ),
                ),
                CollaborationDetailFieldViewModel(
                    "Created",
                    str(item.get("metaText") or state.get("createdAt") or "Timestamp unavailable"),
                ),
                CollaborationDetailFieldViewModel(
                    "Source",
                    str(route_id or "No linked source route"),
                ),
            ),
            activity=CollaborationCollectionViewModel(
                title="Activity",
                subtitle="Related workflow and collaboration events.",
                empty_state="No related activity is available for this collaboration item.",
                items=tuple(self._to_record_view_model(entry) for entry in activity_items),
            ),
            related_items=CollaborationCollectionViewModel(
                title="Related Items",
                subtitle="Open the source workspace or review related project records.",
                empty_state="No related drill-down targets are available for this item.",
                items=tuple(self._to_record_view_model(entry) for entry in related),
            ),
            audit=CollaborationCollectionViewModel(
                title="Audit",
                subtitle="Related workflow trace and governance trail.",
                empty_state="No related audit events were found for this item.",
                items=tuple(self._to_record_view_model(entry) for entry in audit_items),
            ),
        )
        return serialize_collaboration_detail_view_model(detail)

    def _matching_items_for_task_or_project(
        self,
        *,
        source_panels: tuple[str, ...],
        task_id: str,
        project_id: str,
        exclude_item_id: str,
    ) -> list[dict[str, object]]:
        matches: list[dict[str, object]] = []
        seen_ids: set[str] = set()
        for panel_id in source_panels:
            for item in self._panel_item_index.get(panel_id, {}).values():
                if str(item.get("id") or "") == exclude_item_id:
                    continue
                state = dict(item.get("state") or {})
                same_task = task_id and str(state.get("taskId") or "") == task_id
                same_project = project_id and str(state.get("projectId") or "") == project_id
                if not same_task and not same_project:
                    continue
                item_id = str(item.get("id") or "")
                if item_id in seen_ids:
                    continue
                seen_ids.add(item_id)
                matches.append(dict(item))
        matches.sort(key=lambda entry: str(dict(entry.get("state") or {}).get("createdAt") or ""), reverse=True)
        return matches[:10]

    @staticmethod
    def _to_record_view_model(item: dict[str, object]) -> CollaborationRecordViewModel:
        state = dict(item.get("state") or {})
        return CollaborationRecordViewModel(
            id=str(item.get("id") or ""),
            title=str(item.get("title") or ""),
            status_label=str(item.get("statusLabel") or ""),
            subtitle=str(item.get("subtitle") or ""),
            supporting_text=str(item.get("supportingText") or ""),
            meta_text=str(item.get("metaText") or ""),
            state=state,
        )

    @staticmethod
    def _panel_label(panel_id: str) -> str:
        labels = {
            "inbox": "Inbox",
            "mentions": "Mentions",
            "approvals": "Approvals",
            "activity": "Activity",
            "team_updates": "Team Updates",
            "audit": "Audit",
        }
        return labels.get(panel_id, "Collaboration")

    def _set_overview(self, overview: dict[str, object]) -> None:
        if overview == self._overview:
            return
        self._overview = overview
        self.overviewChanged.emit()

    def _set_notifications(self, notifications: dict[str, object]) -> None:
        if notifications == self._notifications:
            return
        self._notifications = notifications
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
        self.mentionsChanged.emit()

    def _set_approvals(self, approvals: dict[str, object]) -> None:
        if approvals == self._approvals:
            return
        self._approvals = approvals
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
        self.selectedItemDetailChanged.emit()


__all__ = ["ProjectManagementCollaborationWorkspaceController"]
