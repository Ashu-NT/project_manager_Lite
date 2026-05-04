from __future__ import annotations

from src.core.modules.project_management.api.desktop import (
    ProjectManagementCollaborationDesktopApi,
    build_project_management_collaboration_desktop_api,
)
from src.ui_qml.modules.project_management.view_models.collaboration import (
    CollaborationCollectionViewModel,
    CollaborationMetricViewModel,
    CollaborationOverviewViewModel,
    CollaborationRecordViewModel,
    CollaborationWorkspaceViewModel,
)


class ProjectCollaborationWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: ProjectManagementCollaborationDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_project_management_collaboration_desktop_api()

    def build_workspace_state(self, *, limit: int = 200) -> CollaborationWorkspaceViewModel:
        snapshot = self._desktop_api.build_snapshot(limit=limit)
        notifications = self._build_notifications_collection(snapshot.notifications)
        inbox = self._build_inbox_collection(snapshot.inbox)
        recent_activity = self._build_recent_activity_collection(snapshot.recent_activity)
        active_presence = self._build_active_presence_collection(snapshot.active_presence)
        unread_count = sum(1 for item in snapshot.inbox if item.unread)
        return CollaborationWorkspaceViewModel(
            overview=CollaborationOverviewViewModel(
                title="Collaboration",
                subtitle="Track mentions, workflow notifications, active editing, and recent task updates across accessible projects.",
                metrics=(
                    CollaborationMetricViewModel(
                        label="Unread mentions",
                        value=str(unread_count),
                        supporting_text=f"{len(snapshot.inbox)} mention thread(s) currently visible.",
                    ),
                    CollaborationMetricViewModel(
                        label="Notifications",
                        value=str(len(snapshot.notifications)),
                        supporting_text="Approval, timesheet, and PM workflow events in the current workspace scope.",
                    ),
                    CollaborationMetricViewModel(
                        label="Recent updates",
                        value=str(len(snapshot.recent_activity)),
                        supporting_text="Latest collaboration comments across accessible project tasks.",
                    ),
                    CollaborationMetricViewModel(
                        label="Active now",
                        value=str(len(snapshot.active_presence)),
                        supporting_text="People currently active in task collaboration or review flows.",
                    ),
                ),
            ),
            notifications=notifications,
            inbox=inbox,
            recent_activity=recent_activity,
            active_presence=active_presence,
            empty_state=self._build_workspace_empty_state(
                notifications=notifications,
                inbox=inbox,
                recent_activity=recent_activity,
                active_presence=active_presence,
            ),
        )

    def mark_task_mentions_read(self, task_id: str) -> None:
        self._desktop_api.mark_task_mentions_read(task_id)

    @staticmethod
    def _build_notifications_collection(notifications) -> CollaborationCollectionViewModel:
        return CollaborationCollectionViewModel(
            title="Notifications",
            subtitle="Workflow notifications for PM activity, approvals, and timesheet review across projects you can access.",
            empty_state=(
                "No collaboration notifications are available yet."
                if not notifications
                else ""
            ),
            items=tuple(
                CollaborationRecordViewModel(
                    id=f"{notification.entity_type}:{notification.entity_id}",
                    title=notification.headline,
                    status_label=(
                        "Needs attention"
                        if notification.attention
                        else notification.notification_type_label
                    ),
                    subtitle=" | ".join(
                        value
                        for value in (
                            notification.project_name or "Cross-project activity",
                            f"From @{notification.actor_username}",
                        )
                        if value
                    ),
                    supporting_text=notification.body_preview or "No preview available.",
                    meta_text=notification.created_at_label,
                    state={
                        "entityId": notification.entity_id,
                        "entityType": notification.entity_type,
                        "notificationType": notification.notification_type,
                        "projectId": notification.project_id or "",
                        "attention": notification.attention,
                    },
                )
                for notification in notifications
            ),
        )

    @staticmethod
    def _build_inbox_collection(inbox) -> CollaborationCollectionViewModel:
        return CollaborationCollectionViewModel(
            title="Mentions",
            subtitle="Mentions needing review. Mark a task as read once the follow-up is complete.",
            empty_state=(
                "No direct mentions need review right now."
                if not inbox
                else ""
            ),
            items=tuple(
                CollaborationRecordViewModel(
                    id=item.comment_id,
                    title=item.task_name,
                    status_label="Unread" if item.unread else "Read",
                    subtitle=" | ".join(
                        value
                        for value in (
                            item.project_name,
                            f"From @{item.author_username}",
                        )
                        if value
                    ),
                    supporting_text=item.body_preview or item.mentions_label,
                    meta_text=f"{item.mentions_label} | {item.created_at_label}",
                    can_primary_action=item.unread,
                    state={
                        "taskId": item.task_id,
                        "commentId": item.comment_id,
                        "projectId": item.project_id,
                        "unread": item.unread,
                    },
                )
                for item in inbox
            ),
        )

    @staticmethod
    def _build_recent_activity_collection(recent_activity) -> CollaborationCollectionViewModel:
        return CollaborationCollectionViewModel(
            title="Recent Activity",
            subtitle="Recent PM collaboration updates across the accessible project set.",
            empty_state=(
                "No recent collaboration activity is available yet."
                if not recent_activity
                else ""
            ),
            items=tuple(
                CollaborationRecordViewModel(
                    id=item.comment_id,
                    title=item.task_name,
                    status_label="Mentions" if item.mentions else "Comment",
                    subtitle=" | ".join(
                        value
                        for value in (
                            item.project_name,
                            f"From @{item.author_username}",
                        )
                        if value
                    ),
                    supporting_text=item.body_preview or "No preview available.",
                    meta_text=f"{item.mentions_label} | {item.created_at_label}",
                    state={
                        "taskId": item.task_id,
                        "commentId": item.comment_id,
                        "projectId": item.project_id,
                    },
                )
                for item in recent_activity
            ),
        )

    @staticmethod
    def _build_active_presence_collection(active_presence) -> CollaborationCollectionViewModel:
        return CollaborationCollectionViewModel(
            title="Active Now",
            subtitle="People currently active in PM task collaboration and edit flows.",
            empty_state=(
                "No active collaboration presence is visible right now."
                if not active_presence
                else ""
            ),
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
                        "taskId": item.task_id,
                        "projectId": item.project_id,
                        "username": item.username,
                        "isSelf": item.is_self,
                    },
                )
                for item in active_presence
            ),
        )

    @staticmethod
    def _build_workspace_empty_state(
        *,
        notifications: CollaborationCollectionViewModel,
        inbox: CollaborationCollectionViewModel,
        recent_activity: CollaborationCollectionViewModel,
        active_presence: CollaborationCollectionViewModel,
    ) -> str:
        if any(
            collection.items
            for collection in (
                notifications,
                inbox,
                recent_activity,
                active_presence,
            )
        ):
            return ""
        return "No collaboration activity is available for the accessible project scope yet."


__all__ = ["ProjectCollaborationWorkspacePresenter"]
