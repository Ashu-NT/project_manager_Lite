from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.domain.collaboration import (
    CollaborationMentionCandidate,
    TaskComment,
)
from src.core.modules.project_management.access.scope_permissions import require_project_permission
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.application.security.authorization import get_authorization_engine


@dataclass(frozen=True)
class TaskCommentActionContext:
    principal_user_id: str
    can_read: bool
    can_manage: bool


class CollaborationCommentQueryMixin:
    def list_comments(self, task_id: str) -> list[TaskComment]:
        task = self._require_task(task_id)
        require_permission(self._user_session, "collaboration.read", operation_label="view task collaboration")
        require_project_permission(
            self._user_session,
            task.project_id,
            "collaboration.read",
            operation_label="view task collaboration",
        )
        return self._comment_repo.list_by_task(task_id)

    def list_mention_candidates(self, task_id: str) -> list[CollaborationMentionCandidate]:
        task = self._require_task(task_id)
        require_permission(self._user_session, "collaboration.read", operation_label="view mention candidates")
        require_project_permission(
            self._user_session,
            task.project_id,
            "collaboration.read",
            operation_label="view mention candidates",
        )
        return self._list_mention_candidates_for_project(task.project_id)

    def unread_mentions_count(self) -> int:
        return sum(1 for item in self.list_inbox(limit=500) if item.unread)

    def get_task_comment_action_context(
        self,
        task_id: str,
    ) -> TaskCommentActionContext:
        """Return server-computed capabilities for task comment presentation."""
        task = self._require_task(task_id)
        engine = get_authorization_engine()
        principal = (
            self._user_session.principal
            if self._user_session is not None
            else None
        )
        principal_user_id = str(getattr(principal, "user_id", "") or "").strip()

        can_read = engine.has_permission(
            self._user_session,
            "collaboration.read",
        ) and engine.has_scope_permission(
            self._user_session,
            "project",
            task.project_id,
            "collaboration.read",
        )
        can_manage = engine.has_permission(
            self._user_session,
            "collaboration.manage",
        ) and engine.has_scope_permission(
            self._user_session,
            "project",
            task.project_id,
            "collaboration.manage",
        )
        return TaskCommentActionContext(
            principal_user_id=principal_user_id,
            can_read=can_read,
            can_manage=can_manage,
        )


__all__ = ["CollaborationCommentQueryMixin", "TaskCommentActionContext"]
