from __future__ import annotations

from src.core.modules.project_management.domain.collaboration import (
    CollaborationInboxItem,
    CollaborationWorkspaceSnapshot,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission


class CollaborationInboxQueryMixin:
    def list_inbox(self, *, limit: int = 200) -> list[CollaborationInboxItem]:
        require_permission(self._user_session, "collaboration.read", operation_label="view collaboration inbox")
        facts, _project_names = self._read_cross_project_collaboration_facts(comment_limit=limit)
        return self._build_comment_items(
            limit=limit,
            comments=facts.comments,
            mentions_only=True,
        )

    def list_recent_activity(self, *, limit: int = 200) -> list[CollaborationInboxItem]:
        require_permission(self._user_session, "collaboration.read", operation_label="view collaboration activity")
        facts, _project_names = self._read_cross_project_collaboration_facts(comment_limit=limit)
        return self._build_comment_items(
            limit=limit,
            comments=facts.comments,
            mentions_only=False,
        )

    def list_workspace_snapshot(self, *, limit: int = 200) -> CollaborationWorkspaceSnapshot:
        require_permission(self._user_session, "collaboration.read", operation_label="view collaboration workspace")
        facts, project_name_by_id = self._read_cross_project_collaboration_facts(
            comment_limit=limit,
            presence_limit=limit,
        )
        inbox = self._build_comment_items(
            limit=limit,
            comments=facts.comments,
            mentions_only=True,
        )
        activity = self._build_comment_items(
            limit=limit,
            comments=facts.comments,
            mentions_only=False,
        )
        notifications = self._build_notifications(
            limit=limit,
            inbox_items=inbox,
            project_name_by_id=project_name_by_id,
        )
        active_presence = self._presence_items_from_facts(facts.active_presence)
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
        comments,
        mentions_only: bool,
    ) -> list[CollaborationInboxItem]:
        items: list[CollaborationInboxItem] = []
        for comment in comments:
            if mentions_only and not self._comment_mentions_principal(comment):
                continue
            items.append(
                CollaborationInboxItem(
                    comment_id=comment.comment_id,
                    task_id=comment.task_id,
                    task_name=comment.task_name,
                    project_id=comment.project_id,
                    project_name=comment.project_name,
                    author_username=comment.author_username or "unknown",
                    body_preview=self._body_preview(comment.body),
                    mentions=list(comment.mentions or []),
                    created_at=comment.created_at,
                    unread=self._comment_is_unread_for_principal(comment),
                )
            )
        return sorted(items, key=lambda item: item.created_at, reverse=True)[:limit]


__all__ = ["CollaborationInboxQueryMixin"]
