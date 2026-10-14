from __future__ import annotations

from src.core.modules.project_management.application.collaboration.utils.visibility import (
    CollaborationVisibilityPolicy,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.common.pagination import (
    PageRequest,
    normalize_page_for_total,
)
from src.core.modules.project_management.contracts.reads.collaboration import (
    CollaborationWorkspaceReader,
)
from src.core.modules.project_management.contracts.reads.collaboration.models.workspace_facts import (
    CollaborationCommentCriteria,
)
from src.core.modules.project_management.domain.collaboration import (
    CollaborationContextOptions,
    CollaborationInboxItem,
    CollaborationInboxPage,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)


def _body_preview(body: str) -> str:
    text = " ".join((body or "").split())
    return text if len(text) <= 120 else f"{text[:117]}..."


class CollaborationInboxQueryHandler(ProjectManagementModuleGuardMixin):
    """Bounded inbox / mentions / recent-activity reads scoped to accessible projects."""

    def __init__(
        self,
        *,
        workspace_reader: CollaborationWorkspaceReader,
        policy: CollaborationVisibilityPolicy,
        tenant_context_service,
        user_session=None,
        module_catalog_service=None,
    ) -> None:
        self._workspace_reader = workspace_reader
        self._policy = policy
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def query_inbox_page(
        self,
        *,
        project_id: str | None = None,
        author_username: str | None = None,
        search_text: str = "",
        created_since=None,
        unread_only: bool = False,
        page: int = 1,
        page_size: int = 25,
    ) -> CollaborationInboxPage:
        return self._query_comment_page(
            operation_label="view collaboration inbox",
            project_id=project_id,
            author_username=author_username,
            search_text=search_text,
            created_since=created_since,
            unread_only=unread_only,
            principal_mentions_only=True,
            page=page,
            page_size=page_size,
        )

    def query_mentions_page(
        self,
        *,
        project_id: str | None = None,
        author_username: str | None = None,
        search_text: str = "",
        created_since=None,
        unread_only: bool = False,
        page: int = 1,
        page_size: int = 25,
    ) -> CollaborationInboxPage:
        return self._query_comment_page(
            operation_label="view collaboration mentions",
            project_id=project_id,
            author_username=author_username,
            search_text=search_text,
            created_since=created_since,
            unread_only=unread_only,
            principal_mentions_only=True,
            page=page,
            page_size=page_size,
        )

    def unread_mentions_count(self) -> int:
        return self.query_mentions_page(unread_only=True, page=1, page_size=1).total

    def list_recent_activity(
        self,
        *,
        project_id: str | None = None,
        author_username: str | None = None,
        created_since=None,
        limit: int = 100,
    ) -> list[CollaborationInboxItem]:
        page = self._query_comment_page(
            operation_label="view recent collaboration activity",
            project_id=project_id,
            author_username=author_username,
            created_since=created_since,
            principal_mentions_only=False,
            page=1,
            page_size=limit,
        )
        return list(page.items)

    def list_workspace_context(self) -> CollaborationContextOptions:
        require_permission(
            self._user_session,
            "collaboration.read",
            operation_label="view collaboration workspace context",
        )
        scope, project_names = self._policy.collaboration_scope(
            operation_label="view collaboration workspace context"
        )
        people = self._workspace_reader.read_comment_authors(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            accessible_project_ids=tuple(project_names),
        )
        return CollaborationContextOptions(
            projects=tuple(sorted(project_names.items(), key=lambda item: item[1].casefold())),
            people=people,
        )

    def _query_comment_page(
        self,
        *,
        operation_label: str,
        project_id: str | None = None,
        author_username: str | None = None,
        search_text: str = "",
        created_since=None,
        unread_only: bool = False,
        principal_mentions_only: bool,
        page: int,
        page_size: int,
    ) -> CollaborationInboxPage:
        require_permission(
            self._user_session,
            "collaboration.read",
            operation_label=operation_label,
        )
        request = PageRequest(page=page, page_size=page_size)
        scope, project_names = self._policy.collaboration_scope(operation_label=operation_label)
        normalized_project_id = str(project_id or "").strip() or None
        if normalized_project_id is not None and normalized_project_id not in project_names:
            return CollaborationInboxPage(page=1, page_size=request.page_size)

        principal = self._policy.principal
        principal_user_id = str(getattr(principal, "user_id", "") or "").strip() or None
        criteria = CollaborationCommentCriteria(
            project_id=normalized_project_id,
            author_username=str(author_username or "").strip() or None,
            search_text=str(search_text or "").strip(),
            created_since=created_since,
            mention_aliases=(
                tuple(sorted(self._policy.principal_aliases()))
                if principal_mentions_only
                else ()
            ),
            principal_user_id=(principal_user_id if principal_mentions_only else None),
            principal_mentions_only=principal_mentions_only,
            unread_only=bool(unread_only),
        )
        def read_page(page_number: int):
            return self._workspace_reader.read_comment_page(
                tenant_id=scope.tenant_id,
                organization_id=scope.organization_id,
                accessible_project_ids=tuple(project_names),
                criteria=criteria,
                page=page_number,
                page_size=request.page_size,
            )

        result = read_page(request.page)
        normalized_page = normalize_page_for_total(
            page=result.page,
            page_size=result.page_size,
            total=result.total,
        )
        if normalized_page != result.page:
            result = read_page(normalized_page)
        return CollaborationInboxPage(
            items=tuple(
                CollaborationInboxItem(
                    comment_id=comment.comment_id,
                    task_id=comment.task_id,
                    task_name=comment.task_name,
                    project_id=comment.project_id,
                    project_name=comment.project_name,
                    author_username=comment.author_username or "unknown",
                    body_preview=_body_preview(comment.body),
                    is_deleted=comment.is_deleted,
                    deleted_at=comment.deleted_at,
                    mentions=list(comment.mentions),
                    created_at=comment.created_at,
                    unread=(
                        self._policy.comment_is_unread_for_principal(comment)
                        if principal_mentions_only
                        else False
                    ),
                )
                for comment in result.items
            ),
            total=result.total,
            page=result.page,
            page_size=result.page_size,
        )


__all__ = ["CollaborationInboxQueryHandler"]
