from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.api.desktop.platform import ApprovalDecisionCommand, PlatformApprovalDesktopApi
from src.core.modules.project_management.api.desktop import (
    ProjectManagementCollaborationDesktopApi,
    build_project_management_collaboration_desktop_api,
)
from src.ui_qml.modules.project_management.view_models.collaboration import (
    CollaborationCollectionViewModel,
    CollaborationContextViewModel,
    CollaborationMetricViewModel,
    CollaborationOptionViewModel,
    CollaborationOverviewViewModel,
    CollaborationPanelTabViewModel,
    CollaborationRecordViewModel,
    CollaborationWorkspaceViewModel,
)


class ProjectCollaborationWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: ProjectManagementCollaborationDesktopApi | None = None,
        approval_api: PlatformApprovalDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_project_management_collaboration_desktop_api()
        self._approval_api = approval_api

    def build_workspace_state(self, *, limit: int = 200) -> CollaborationWorkspaceViewModel:
        snapshot = self._desktop_api.build_snapshot(limit=limit)
        inbox = self._build_inbox_collection(snapshot.notifications)
        mentions = self._build_mentions_collection(snapshot.inbox)
        approvals = self._build_approvals_collection(limit=limit)
        activity_feed = self._build_activity_collection(
            notifications=snapshot.notifications,
            recent_activity=snapshot.recent_activity,
        )
        active_presence = self._build_active_presence_collection(snapshot.active_presence)
        team_updates = self._build_team_updates_collection(snapshot.active_presence)
        audit_feed = self._build_audit_collection(
            notifications=snapshot.notifications,
            recent_activity=snapshot.recent_activity,
        )
        unread_count = sum(1 for item in snapshot.inbox if item.unread)
        attention_count = sum(1 for item in snapshot.notifications if item.attention)
        approval_count = len(approvals.items)
        active_users_count = len(snapshot.active_presence)
        context = self._build_context_view_model(
            inbox=inbox,
            mentions=mentions,
            approvals=approvals,
            activity_feed=activity_feed,
            team_updates=team_updates,
            audit_feed=audit_feed,
        )
        panel_tabs = (
            CollaborationPanelTabViewModel("inbox", "Inbox", len(inbox.items)),
            CollaborationPanelTabViewModel("mentions", "Mentions", len(mentions.items)),
            CollaborationPanelTabViewModel("approvals", "Approvals", len(approvals.items)),
            CollaborationPanelTabViewModel("activity", "Activity", len(activity_feed.items)),
            CollaborationPanelTabViewModel("team_updates", "Team Updates", len(team_updates.items)),
            CollaborationPanelTabViewModel("audit", "Audit", len(audit_feed.items)),
        )
        return CollaborationWorkspaceViewModel(
            overview=CollaborationOverviewViewModel(
                title="Collaboration",
                subtitle=(
                    "Workflow inbox, operational communication, mentions, approvals, and activity feed "
                    "across the accessible project scope."
                ),
                metrics=(
                    CollaborationMetricViewModel(
                        label="Unread",
                        value=str(unread_count),
                        supporting_text="Direct mentions and task follow-ups awaiting review.",
                    ),
                    CollaborationMetricViewModel(
                        label="Approvals",
                        value=str(approval_count),
                        supporting_text="Governed approval requests currently visible to the user.",
                    ),
                    CollaborationMetricViewModel(
                        label="Mentions",
                        value=str(len(mentions.items)),
                        supporting_text="Mention threads across active project work.",
                    ),
                    CollaborationMetricViewModel(
                        label="Reviews",
                        value=str(attention_count),
                        supporting_text="Workflow items currently flagged as needing attention.",
                    ),
                    CollaborationMetricViewModel(
                        label="Active Users",
                        value=str(active_users_count),
                        supporting_text="People currently active in task collaboration or review flows.",
                    ),
                    CollaborationMetricViewModel(
                        label="Workflow Alerts",
                        value=str(len(inbox.items)),
                        supporting_text="Operational workflow items in the inbox stream.",
                    ),
                ),
            ),
            notifications=inbox,
            inbox=mentions,
            recent_activity=activity_feed,
            active_presence=active_presence,
            context=context,
            panel_tabs=panel_tabs,
            mentions=mentions,
            approvals=approvals,
            activity_feed=activity_feed,
            team_updates=team_updates,
            audit_feed=audit_feed,
            empty_state=self._build_workspace_empty_state(
                inbox=inbox,
                mentions=mentions,
                approvals=approvals,
                activity_feed=activity_feed,
                team_updates=team_updates,
                audit_feed=audit_feed,
            ),
        )

    def mark_task_mentions_read(self, task_id: str) -> None:
        self._desktop_api.mark_task_mentions_read(task_id)

    def approve_request(self, request_id: str, *, note: str | None = None) -> None:
        if self._approval_api is None:
            raise RuntimeError("Platform approval API is not connected.")
        result = self._approval_api.approve_and_apply(
            ApprovalDecisionCommand(
                request_id=request_id,
                note=(note or "").strip() or None,
            )
        )
        if not result.ok:
            message = result.error.message if result.error is not None else "Unable to approve the workflow item."
            raise RuntimeError(message)

    def reject_request(self, request_id: str, *, note: str | None = None) -> None:
        if self._approval_api is None:
            raise RuntimeError("Platform approval API is not connected.")
        result = self._approval_api.reject(
            ApprovalDecisionCommand(
                request_id=request_id,
                note=(note or "").strip() or None,
            )
        )
        if not result.ok:
            message = result.error.message if result.error is not None else "Unable to reject the workflow item."
            raise RuntimeError(message)

    def _build_inbox_collection(self, notifications) -> CollaborationCollectionViewModel:
        return CollaborationCollectionViewModel(
            title="Inbox",
            subtitle="Operational workflow inbox for mentions, approvals, timesheets, and PM alerts.",
            empty_state="No workflow inbox items are visible right now.",
            items=tuple(
                CollaborationRecordViewModel(
                    id=f"inbox:{notification.entity_type}:{notification.entity_id}",
                    title=notification.headline,
                    status_label=(
                        "Needs Attention"
                        if notification.attention
                        else notification.notification_type_label
                    ),
                    subtitle=" | ".join(
                        value
                        for value in (
                            notification.notification_type_label,
                            notification.project_name or "Cross-project",
                        )
                        if value
                    ),
                    supporting_text=notification.body_preview or "No preview available.",
                    meta_text=f"From @{notification.actor_username} | {notification.created_at_label}",
                    can_primary_action=notification.attention,
                    state={
                        "panelId": "inbox",
                        "routeId": self._notification_route_id(notification),
                        "projectId": notification.project_id or "",
                        "projectName": notification.project_name or "",
                        "taskId": getattr(notification, "task_id", "") or "",
                        "entityId": notification.entity_id,
                        "entityType": notification.entity_type,
                        "notificationType": notification.notification_type,
                        "actorUsername": notification.actor_username,
                        "attention": notification.attention,
                        "createdAt": _iso_datetime(notification.created_at),
                    },
                )
                for notification in notifications
            ),
        )

    def _build_mentions_collection(self, inbox) -> CollaborationCollectionViewModel:
        return CollaborationCollectionViewModel(
            title="Mentions",
            subtitle="Direct mentions needing follow-up or acknowledgment.",
            empty_state="No direct mentions need review right now.",
            items=tuple(
                CollaborationRecordViewModel(
                    id=item.comment_id,
                    title=item.task_name,
                    status_label="Unread" if item.unread else "Read",
                    subtitle=" | ".join(
                        value
                        for value in (
                            item.task_name,
                            item.project_name,
                        )
                        if value
                    ),
                    supporting_text=f"From @{item.author_username} | {item.mentions_label}",
                    meta_text=item.created_at_label,
                    can_primary_action=item.unread,
                    state={
                        "panelId": "mentions",
                        "routeId": "project_management.tasks",
                        "projectId": item.project_id,
                        "projectName": item.project_name,
                        "taskId": item.task_id,
                        "commentId": item.comment_id,
                        "actorUsername": item.author_username,
                        "mentionsLabel": item.mentions_label,
                        "unread": item.unread,
                        "createdAt": _iso_datetime(item.created_at),
                    },
                )
                for item in inbox
            ),
        )

    def _build_approvals_collection(self, *, limit: int) -> CollaborationCollectionViewModel:
        if self._approval_api is None:
            return CollaborationCollectionViewModel(
                title="Approvals",
                subtitle="Platform approval API is not connected in this QML preview.",
                empty_state="No approval requests are available yet.",
            )
        result = self._approval_api.list_requests(status=None, limit=limit)
        if not result.ok or result.data is None:
            message = result.error.message if result.error is not None else "Unable to load approvals."
            return CollaborationCollectionViewModel(
                title="Approvals",
                subtitle=message,
                empty_state=message,
            )
        return CollaborationCollectionViewModel(
            title="Approvals",
            subtitle="Governed workflow approvals linked to project execution and operational delivery.",
            empty_state="No approval requests are available right now.",
            items=tuple(
                CollaborationRecordViewModel(
                    id=row.id,
                    title=row.display_label or row.request_type.replace("_", " ").title(),
                    status_label=row.status.value.title(),
                    subtitle=" | ".join(
                        value
                        for value in (
                            row.module_label,
                            row.context_label,
                        )
                        if value
                    ),
                    supporting_text=f"Requested by @{row.requested_by_username or 'system'}",
                    meta_text=_format_timestamp(row.requested_at),
                    can_primary_action=row.status.value.upper() == "PENDING",
                    can_secondary_action=row.status.value.upper() == "PENDING",
                    state={
                        "panelId": "approvals",
                        "routeId": "platform.control",
                        "projectId": row.project_id or "",
                        "requestId": row.id,
                        "entityId": row.entity_id,
                        "entityType": row.entity_type,
                        "requestType": row.request_type,
                        "moduleLabel": row.module_label,
                        "contextLabel": row.context_label,
                        "requestor": row.requested_by_username or "system",
                        "createdAt": _iso_datetime(row.requested_at),
                        "status": row.status.value,
                    },
                )
                for row in result.data
            ),
        )

    def _build_activity_collection(
        self,
        *,
        notifications,
        recent_activity,
    ) -> CollaborationCollectionViewModel:
        activity_rows = []
        for notification in notifications:
            activity_rows.append(
                CollaborationRecordViewModel(
                    id=f"activity-note:{notification.entity_type}:{notification.entity_id}",
                    title=notification.headline,
                    status_label=notification.notification_type_label,
                    subtitle=notification.project_name or "Cross-project activity",
                    supporting_text=notification.body_preview or f"From @{notification.actor_username}",
                    meta_text=notification.created_at_label,
                    state={
                        "panelId": "activity",
                        "routeId": self._notification_route_id(notification),
                        "projectId": notification.project_id or "",
                        "projectName": notification.project_name or "",
                        "actorUsername": notification.actor_username,
                        "entityId": notification.entity_id,
                        "entityType": notification.entity_type,
                        "createdAt": _iso_datetime(notification.created_at),
                    },
                )
            )
        for item in recent_activity:
            activity_rows.append(
                CollaborationRecordViewModel(
                    id=f"activity-comment:{item.comment_id}",
                    title=item.task_name,
                    status_label="Mention" if item.mentions else "Comment",
                    subtitle=item.project_name,
                    supporting_text=item.body_preview or item.mentions_label,
                    meta_text=f"{item.created_at_label} | @{item.author_username}",
                    state={
                        "panelId": "activity",
                        "routeId": "project_management.tasks",
                        "projectId": item.project_id,
                        "projectName": item.project_name,
                        "taskId": item.task_id,
                        "commentId": item.comment_id,
                        "actorUsername": item.author_username,
                        "mentionsLabel": item.mentions_label,
                        "createdAt": _iso_datetime(item.created_at),
                    },
                )
            )
        return CollaborationCollectionViewModel(
            title="Activity",
            subtitle="Workflow and collaboration activity across accessible project operations.",
            empty_state="No workflow activity is available yet.",
            items=_sort_records_by_created_desc(tuple(activity_rows)),
        )

    def _build_active_presence_collection(self, active_presence) -> CollaborationCollectionViewModel:
        return CollaborationCollectionViewModel(
            title="Active Now",
            subtitle="People currently active in PM task collaboration and review flows.",
            empty_state="No active collaboration presence is visible right now.",
            items=tuple(
                CollaborationRecordViewModel(
                    id=f"{item.task_id}:{item.username}",
                    title=item.task_name,
                    status_label=item.activity_label,
                    subtitle=item.project_name,
                    supporting_text=item.who_label,
                    meta_text=(
                        f"Last seen {item.last_seen_at_label}"
                        + (" | You" if item.is_self else "")
                    ),
                    state={
                        "panelId": "team_updates",
                        "routeId": "project_management.tasks",
                        "projectId": item.project_id,
                        "projectName": item.project_name,
                        "taskId": item.task_id,
                        "taskName": item.task_name,
                        "username": item.username,
                        "displayName": item.display_name or "",
                        "activity": item.activity,
                        "createdAt": _iso_datetime(item.last_seen_at),
                    },
                )
                for item in active_presence
            ),
        )

    def _build_team_updates_collection(self, active_presence) -> CollaborationCollectionViewModel:
        return CollaborationCollectionViewModel(
            title="Team Updates",
            subtitle="Active users currently editing, reviewing, or monitoring PM task workflows.",
            empty_state="No active collaboration presence is visible right now.",
            items=tuple(
                CollaborationRecordViewModel(
                    id=f"{item.task_id}:{item.username}",
                    title=item.who_label,
                    status_label=item.activity_label,
                    subtitle=" | ".join(
                        value
                        for value in (
                            item.task_name,
                            item.project_name,
                        )
                        if value
                    ),
                    supporting_text=f"Last seen {item.last_seen_at_label}",
                    meta_text="You" if item.is_self else f"@{item.username}",
                    state={
                        "panelId": "team_updates",
                        "routeId": "project_management.tasks",
                        "projectId": item.project_id,
                        "projectName": item.project_name,
                        "taskId": item.task_id,
                        "taskName": item.task_name,
                        "username": item.username,
                        "displayName": item.display_name or "",
                        "activity": item.activity,
                        "createdAt": _iso_datetime(item.last_seen_at),
                    },
                )
                for item in active_presence
            ),
        )

    def _build_audit_collection(
        self,
        *,
        notifications,
        recent_activity,
    ) -> CollaborationCollectionViewModel:
        audit_rows = []
        for notification in notifications:
            audit_rows.append(
                CollaborationRecordViewModel(
                    id=f"audit-note:{notification.entity_type}:{notification.entity_id}",
                    title=notification.headline,
                    status_label=notification.notification_type_label,
                    subtitle=notification.project_name or "Cross-project workflow",
                    supporting_text=f"From @{notification.actor_username}",
                    meta_text=notification.created_at_label,
                    state={
                        "panelId": "audit",
                        "routeId": self._notification_route_id(notification),
                        "projectId": notification.project_id or "",
                        "entityId": notification.entity_id,
                        "entityType": notification.entity_type,
                        "createdAt": _iso_datetime(notification.created_at),
                    },
                )
            )
        for item in recent_activity:
            audit_rows.append(
                CollaborationRecordViewModel(
                    id=f"audit-comment:{item.comment_id}",
                    title=item.task_name,
                    status_label="Comment Trail",
                    subtitle=item.project_name,
                    supporting_text=item.body_preview or item.mentions_label,
                    meta_text=f"{item.created_at_label} | @{item.author_username}",
                    state={
                        "panelId": "audit",
                        "routeId": "project_management.tasks",
                        "projectId": item.project_id,
                        "taskId": item.task_id,
                        "commentId": item.comment_id,
                        "createdAt": _iso_datetime(item.created_at),
                    },
                )
            )
        return CollaborationCollectionViewModel(
            title="Audit",
            subtitle="Trace workflow history, escalations, and collaboration events.",
            empty_state="No workflow audit events are available yet.",
            items=_sort_records_by_created_desc(tuple(audit_rows)),
        )

    def _build_context_view_model(
        self,
        *,
        inbox: CollaborationCollectionViewModel,
        mentions: CollaborationCollectionViewModel,
        approvals: CollaborationCollectionViewModel,
        activity_feed: CollaborationCollectionViewModel,
        team_updates: CollaborationCollectionViewModel,
        audit_feed: CollaborationCollectionViewModel,
    ) -> CollaborationContextViewModel:
        project_options = [CollaborationOptionViewModel("all", "All Projects")]
        seen_projects: set[tuple[str, str]] = set()
        team_options = [CollaborationOptionViewModel("all", "All Teams")]
        seen_teams: set[str] = set()
        for collection in (
            inbox,
            mentions,
            approvals,
            activity_feed,
            team_updates,
            audit_feed,
        ):
            for item in collection.items:
                state = dict(item.state)
                project_id = str(state.get("projectId") or "").strip()
                project_name = str(state.get("projectName") or "").strip()
                if project_id and (project_id, project_name) not in seen_projects:
                    project_options.append(
                        CollaborationOptionViewModel(project_id, project_name or project_id)
                    )
                    seen_projects.add((project_id, project_name))
                team_key = str(
                    state.get("actorUsername")
                    or state.get("requestor")
                    or state.get("username")
                    or ""
                ).strip()
                if team_key and team_key not in seen_teams:
                    team_options.append(
                        CollaborationOptionViewModel(team_key, f"@{team_key}")
                    )
                    seen_teams.add(team_key)
        return CollaborationContextViewModel(
            project_options=tuple(project_options),
            team_options=tuple(team_options),
            period_options=(
                CollaborationOptionViewModel("all", "All Time"),
                CollaborationOptionViewModel("24h", "Last 24 Hours"),
                CollaborationOptionViewModel("7d", "Last 7 Days"),
                CollaborationOptionViewModel("30d", "Last 30 Days"),
            ),
            unread_options=(
                CollaborationOptionViewModel("all", "All Items"),
                CollaborationOptionViewModel("unread", "Unread Only"),
                CollaborationOptionViewModel("attention", "Needs Attention"),
            ),
        )

    def _build_workspace_empty_state(
        self,
        *,
        inbox: CollaborationCollectionViewModel,
        mentions: CollaborationCollectionViewModel,
        approvals: CollaborationCollectionViewModel,
        activity_feed: CollaborationCollectionViewModel,
        team_updates: CollaborationCollectionViewModel,
        audit_feed: CollaborationCollectionViewModel,
    ) -> str:
        if any(
            collection.items
            for collection in (
                inbox,
                mentions,
                approvals,
                activity_feed,
                team_updates,
                audit_feed,
            )
        ):
            return ""
        return "No collaboration or workflow activity is available for the accessible project scope yet."

    @staticmethod
    def _notification_route_id(notification) -> str:
        entity_type = str(getattr(notification, "entity_type", "") or "")
        notification_type = str(getattr(notification, "notification_type", "") or "")
        if entity_type == "approval_request":
            return "platform.control"
        if notification_type == "timesheet":
            return "project_management.timesheets"
        if entity_type == "task_comment" or notification_type == "mention":
            return "project_management.tasks"
        return "project_management.collaboration"


def _sort_records_by_created_desc(
    view_models: tuple[CollaborationRecordViewModel, ...],
) -> tuple[CollaborationRecordViewModel, ...]:
    return tuple(
        sorted(
            view_models,
            key=lambda item: str(item.state.get("createdAt") or ""),
            reverse=True,
        )
    )


def _iso_datetime(value: datetime | None) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def _format_timestamp(value: datetime | None) -> str:
    if value is None:
        return "Timestamp unavailable"
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M")


def _within_period(iso_value: str, period_key: str) -> bool:
    if not iso_value or period_key == "all":
        return True
    try:
        observed = datetime.fromisoformat(iso_value.replace("Z", "+00:00"))
    except ValueError:
        return True
    now = datetime.now(UTC)
    if period_key == "24h":
        return observed >= now - timedelta(hours=24)
    if period_key == "7d":
        return observed >= now - timedelta(days=7)
    if period_key == "30d":
        return observed >= now - timedelta(days=30)
    return True


__all__ = ["ProjectCollaborationWorkspacePresenter", "_within_period"]
