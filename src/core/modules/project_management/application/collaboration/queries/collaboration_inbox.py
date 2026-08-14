from __future__ import annotations

from src.core.modules.project_management.domain.collaboration import (
    CollaborationInboxItem,
    CollaborationInboxPage,
    CollaborationWorkspaceSnapshot,
)
from src.core.modules.project_management.application.common.pagination import PageRequest
from src.core.modules.project_management.contracts.reads.collaboration.models.workspace_facts import (
    CollaborationCommentCriteria,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission


class CollaborationInboxQueryMixin:
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
        require_permission(
            self._user_session,
            "collaboration.read",
            operation_label="view collaboration mentions",
        )
        request = PageRequest(page=page, page_size=page_size)
        scope, project_names = self._collaboration_scope(
            operation_label="view collaboration mentions"
        )
        normalized_project_id = str(project_id or "").strip() or None
        if normalized_project_id is not None and normalized_project_id not in project_names:
            return CollaborationInboxPage(page=request.page, page_size=request.page_size)
        principal = self._user_session.principal if self._user_session is not None else None
        principal_user_id = str(getattr(principal, "user_id", "") or "").strip() or None
        result = self._workspace_reader.read_comment_page(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            accessible_project_ids=tuple(project_names),
            criteria=CollaborationCommentCriteria(
                project_id=normalized_project_id,
                author_username=str(author_username or "").strip() or None,
                search_text=str(search_text or "").strip(),
                created_since=created_since,
                mention_aliases=tuple(sorted(self._principal_aliases())),
                principal_user_id=principal_user_id,
                unread_only=bool(unread_only),
            ),
            page=request.page,
            page_size=request.page_size,
        )
        return CollaborationInboxPage(
            items=tuple(
                CollaborationInboxItem(
                    comment_id=comment.comment_id,
                    task_id=comment.task_id,
                    task_name=comment.task_name,
                    project_id=comment.project_id,
                    project_name=comment.project_name,
                    author_username=comment.author_username or "unknown",
                    body_preview=self._body_preview(comment.body),
                    mentions=list(comment.mentions),
                    created_at=comment.created_at,
                    unread=self._comment_is_unread_for_principal(comment),
                )
                for comment in result.items
            ),
            total=result.total,
            page=result.page,
            page_size=result.page_size,
        )

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
