from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.pagination import (
    PageRequest,
    normalize_page_for_total,
)
from src.core.modules.project_management.contracts.reads.collaboration.models.workspace_facts import (
    TaskDetailCommentReadPage,
)
from src.core.modules.project_management.domain.collaboration import (
    CollaborationMentionCandidate,
)
from src.core.platform.application.security.authorization import (
    get_authorization_engine,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)


@dataclass(frozen=True)
class TaskCommentActionContext:
    principal_user_id: str
    can_read: bool
    can_manage: bool


class CollaborationCommentQueryMixin:
    def query_task_comments_page(
        self, task_id: str, *, page: int = 1, page_size: int = 25
    ) -> TaskDetailCommentReadPage:
        task = self._require_task(task_id)
        require_permission(
            self._user_session, "collaboration.read", operation_label="view task collaboration"
        )
        require_project_permission(
            self._user_session,
            task.project_id,
            "collaboration.read",
            operation_label="view task collaboration",
        )
        request = PageRequest(page=page, page_size=min(page_size, 100))
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view task collaboration"
        )

        def read(page_number: int):
            return self._workspace_reader.read_task_comment_page(
                tenant_id=scope.tenant_id,
                organization_id=scope.organization_id,
                task_id=task_id,
                page=page_number,
                page_size=request.page_size,
            )

        result = read(request.page)
        normalized_page = normalize_page_for_total(
            page=result.page, page_size=result.page_size, total=result.total
        )
        return read(normalized_page) if normalized_page != result.page else result

    def list_mention_candidates(
        self, task_id: str, *, query: str = "", limit: int = 50
    ) -> list[CollaborationMentionCandidate]:
        task = self._require_task(task_id)
        require_permission(self._user_session, "collaboration.read", operation_label="view mention candidates")
        require_project_permission(
            self._user_session,
            task.project_id,
            "collaboration.read",
            operation_label="view mention candidates",
        )
        return self._list_mention_candidates_for_project(
            task.project_id, query=query, limit=max(1, min(limit, 100))
        )

    def unread_mentions_count(self) -> int:
        return self.query_mentions_page(unread_only=True, page=1, page_size=1).total

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
