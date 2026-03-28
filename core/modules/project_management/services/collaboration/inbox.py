from __future__ import annotations

from core.modules.project_management.domain.collaboration import (
    CollaborationInboxItem,
    CollaborationWorkspaceSnapshot,
)
from core.platform.auth.authorization import require_permission


class CollaborationInboxMixin:
    def list_inbox(self, *, limit: int = 200) -> list[CollaborationInboxItem]:
        require_permission(self._user_session, "collaboration.read", operation_label="view collaboration inbox")
        tasks, project_name_by_id = self._accessible_task_context_for_collaboration()
        return self._build_comment_items(
            limit=limit,
            tasks=tasks,
            project_name_by_id=project_name_by_id,
            mentions_only=True,
        )

    def list_recent_activity(self, *, limit: int = 200) -> list[CollaborationInboxItem]:
        require_permission(self._user_session, "collaboration.read", operation_label="view collaboration activity")
        tasks, project_name_by_id = self._accessible_task_context_for_collaboration()
        return self._build_comment_items(
            limit=limit,
            tasks=tasks,
            project_name_by_id=project_name_by_id,
            mentions_only=False,
        )

    def list_workspace_snapshot(self, *, limit: int = 200) -> CollaborationWorkspaceSnapshot:
        require_permission(self._user_session, "collaboration.read", operation_label="view collaboration workspace")
        tasks, project_name_by_id = self._accessible_task_context_for_collaboration()
        inbox = self._build_comment_items(
            limit=limit,
            tasks=tasks,
            project_name_by_id=project_name_by_id,
            mentions_only=True,
        )
        activity = self._build_comment_items(
            limit=limit,
            tasks=tasks,
            project_name_by_id=project_name_by_id,
            mentions_only=False,
        )
        notifications = self._build_notifications(limit=limit, inbox_items=inbox)
        active_presence = self._presence_items_for_tasks(
            tasks=tasks,
            project_name_by_id=project_name_by_id,
            limit=limit,
        )
        return CollaborationWorkspaceSnapshot(
            notifications=notifications,
            inbox=inbox,
            recent_activity=activity,
            active_presence=active_presence,
        )

    def _build_comment_items(
        self,
        *,
        limit: int,
        tasks,
        project_name_by_id: dict[str, str],
        mentions_only: bool,
    ) -> list[CollaborationInboxItem]:
        items: list[CollaborationInboxItem] = []
        task_by_id = {task.id: task for task in tasks}
        if not task_by_id:
            return items
        for comment in self._list_accessible_comments(limit=limit, tasks=tasks):
            if mentions_only and not self._comment_mentions_principal(comment):
                continue
            task = task_by_id.get(comment.task_id)
            if task is None:
                continue
            items.append(
                CollaborationInboxItem(
                    comment_id=comment.id,
                    task_id=task.id,
                    task_name=task.name,
                    project_id=task.project_id,
                    project_name=project_name_by_id.get(task.project_id, ""),
                    author_username=comment.author_username or "unknown",
                    body_preview=self._body_preview(comment.body),
                    mentions=list(comment.mentions or []),
                    created_at=comment.created_at,
                    unread=self._comment_is_unread_for_principal(comment),
                )
            )
        return sorted(items, key=lambda item: item.created_at, reverse=True)[:limit]


__all__ = ["CollaborationInboxMixin"]
