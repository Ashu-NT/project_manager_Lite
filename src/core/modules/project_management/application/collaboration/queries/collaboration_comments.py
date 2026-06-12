from __future__ import annotations

from src.core.modules.project_management.domain.collaboration import (
    CollaborationMentionCandidate,
    TaskComment,
)
from src.core.platform.access.authorization import require_project_permission
from src.core.platform.auth.authorization import require_permission


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


__all__ = ["CollaborationCommentQueryMixin"]
