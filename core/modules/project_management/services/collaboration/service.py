from __future__ import annotations

from typing import Iterable

from sqlalchemy.orm import Session

from core.platform.notifications.domain_events import domain_events
from core.platform.common.exceptions import NotFoundError, ValidationError
from core.platform.common.interfaces import (
    ProjectMembershipRepository,
    ProjectRepository,
    TaskCommentRepository,
    TaskRepository,
    UserRepository,
)
from core.platform.common.models import CollaborationInboxItem, CollaborationMentionCandidate, TaskComment
from core.platform.access.authorization import require_project_permission
from core.platform.auth.authorization import require_permission
from core.modules.project_management.services.collaboration.mentions import resolve_mentions
from infra.modules.project_management.collaboration_attachments import store_task_comment_attachments


class CollaborationService:
    def __init__(
        self,
        *,
        session: Session,
        comment_repo: TaskCommentRepository,
        task_repo: TaskRepository,
        project_repo: ProjectRepository,
        user_repo: UserRepository,
        project_membership_repo: ProjectMembershipRepository,
        user_session=None,
    ) -> None:
        self._session = session
        self._comment_repo = comment_repo
        self._task_repo = task_repo
        self._project_repo = project_repo
        self._user_repo = user_repo
        self._project_membership_repo = project_membership_repo
        self._user_session = user_session

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

    def post_comment(
        self,
        *,
        task_id: str,
        body: str,
        attachments: Iterable[str] | None = None,
    ) -> TaskComment:
        task = self._require_task(task_id)
        require_permission(self._user_session, "collaboration.manage", operation_label="post task collaboration update")
        require_project_permission(
            self._user_session,
            task.project_id,
            "collaboration.manage",
            operation_label="post task collaboration update",
        )
        text = (body or "").strip()
        if not text:
            raise ValidationError("Comment text is required.", code="COLLABORATION_BODY_REQUIRED")

        mention_candidates = self._list_mention_candidates_for_project(task.project_id)
        mentions, mentioned_user_ids, unresolved = resolve_mentions(
            text=text,
            candidates=mention_candidates,
        )
        if unresolved:
            preview = ", ".join(f"@{token}" for token in unresolved[:4])
            raise ValidationError(
                f"Unknown mention handle(s): {preview}. Mention project collaborators with access to this task.",
                code="COLLABORATION_MENTION_UNKNOWN",
            )

        principal = self._user_session.principal if self._user_session is not None else None
        comment = TaskComment.create(
            task_id=task_id,
            author_user_id=getattr(principal, "user_id", None),
            author_username=getattr(principal, "username", None) or "unknown",
            body=text,
            mentions=mentions,
            mentioned_user_ids=mentioned_user_ids,
            attachments=[],
        )
        comment.attachments = store_task_comment_attachments(
            task_id=task_id,
            comment_id=comment.id,
            attachments=[str(item) for item in (attachments or []) if str(item).strip()],
        )
        self._comment_repo.add(comment)
        self._session.commit()
        domain_events.collaboration_changed.emit(task_id)
        return comment

    def mark_task_mentions_read(self, task_id: str) -> None:
        task = self._require_task(task_id)
        require_permission(self._user_session, "collaboration.read", operation_label="mark collaboration updates read")
        require_project_permission(
            self._user_session,
            task.project_id,
            "collaboration.read",
            operation_label="mark collaboration updates read",
        )
        principal = self._user_session.principal if self._user_session is not None else None
        principal_user_id = str(getattr(principal, "user_id", "") or "").strip()
        aliases = self._principal_aliases()
        if not principal_user_id and not aliases:
            return

        changed = False
        for comment in self._comment_repo.list_by_task(task_id):
            if not self._comment_mentions_principal(comment):
                continue

            user_reads = {str(item).strip() for item in comment.read_by_user_ids if str(item).strip()}
            alias_reads = {item.lower() for item in comment.read_by}
            already_read = False
            if principal_user_id and principal_user_id in user_reads:
                already_read = True
            if not already_read and aliases and not alias_reads.isdisjoint(aliases):
                already_read = True
            if already_read:
                continue

            if principal_user_id:
                comment.read_by_user_ids = sorted(user_reads.union({principal_user_id}))
            primary_alias = self._principal_primary_alias()
            if primary_alias:
                comment.read_by = sorted(alias_reads.union({primary_alias}))
            self._comment_repo.update(comment)
            changed = True

        if changed:
            self._session.commit()
            domain_events.collaboration_changed.emit(task_id)

    def unread_mentions_count(self) -> int:
        return sum(1 for item in self.list_inbox(limit=500) if item.unread)

    def list_inbox(self, *, limit: int = 200) -> list[CollaborationInboxItem]:
        require_permission(self._user_session, "collaboration.read", operation_label="view collaboration inbox")
        items: list[CollaborationInboxItem] = []
        for comment in self._list_accessible_comments(limit=limit):
            if not self._comment_mentions_principal(comment):
                continue
            task = self._task_repo.get(comment.task_id)
            if task is None:
                continue
            project = self._project_repo.get(task.project_id)
            if project is None:
                continue
            items.append(
                CollaborationInboxItem(
                    comment_id=comment.id,
                    task_id=task.id,
                    task_name=task.name,
                    project_id=project.id,
                    project_name=project.name,
                    author_username=comment.author_username or "unknown",
                    body_preview=self._body_preview(comment.body),
                    mentions=list(comment.mentions or []),
                    created_at=comment.created_at,
                    unread=self._comment_is_unread_for_principal(comment),
                )
            )
        return sorted(items, key=lambda item: item.created_at, reverse=True)[:limit]

    def list_recent_activity(self, *, limit: int = 200) -> list[CollaborationInboxItem]:
        require_permission(self._user_session, "collaboration.read", operation_label="view collaboration activity")
        items: list[CollaborationInboxItem] = []
        for comment in self._list_accessible_comments(limit=limit):
            task = self._task_repo.get(comment.task_id)
            if task is None:
                continue
            project = self._project_repo.get(task.project_id)
            if project is None:
                continue
            items.append(
                CollaborationInboxItem(
                    comment_id=comment.id,
                    task_id=task.id,
                    task_name=task.name,
                    project_id=project.id,
                    project_name=project.name,
                    author_username=comment.author_username or "unknown",
                    body_preview=self._body_preview(comment.body),
                    mentions=[item.lower() for item in comment.mentions],
                    created_at=comment.created_at,
                    unread=self._comment_is_unread_for_principal(comment),
                )
            )
        return sorted(items, key=lambda item: item.created_at, reverse=True)[:limit]

    def _list_accessible_comments(self, *, limit: int) -> list[TaskComment]:
        accessible_task_ids: list[str] = []
        for project in self._project_repo.list_all():
            if self._user_session is None:
                continue
            if not self._user_session.has_project_permission(project.id, "collaboration.read"):
                continue
            for task in self._task_repo.list_by_project(project.id):
                accessible_task_ids.append(task.id)
        return self._comment_repo.list_recent_for_tasks(accessible_task_ids, limit=limit)

    def _list_mention_candidates_for_project(self, project_id: str) -> list[CollaborationMentionCandidate]:
        candidates: list[CollaborationMentionCandidate] = []
        seen_user_ids: set[str] = set()
        for membership in self._project_membership_repo.list_by_project(project_id):
            permissions = {str(code).strip() for code in membership.permission_codes}
            if permissions.isdisjoint({"collaboration.read", "collaboration.manage"}):
                continue
            user = self._user_repo.get(membership.user_id)
            if user is None or not user.is_active:
                continue
            if user.id in seen_user_ids:
                continue
            seen_user_ids.add(user.id)
            candidates.append(
                CollaborationMentionCandidate(
                    user_id=user.id,
                    username=user.username,
                    display_name=user.display_name,
                    scope_role=membership.scope_role,
                )
            )

        principal = self._user_session.principal if self._user_session is not None else None
        principal_user_id = str(getattr(principal, "user_id", "") or "").strip()
        if principal_user_id and principal_user_id not in seen_user_ids:
            if self._user_session is not None and self._user_session.has_project_permission(project_id, "collaboration.read"):
                user = self._user_repo.get(principal_user_id)
                if user is not None and user.is_active:
                    candidates.append(
                        CollaborationMentionCandidate(
                            user_id=user.id,
                            username=user.username,
                            display_name=user.display_name,
                            scope_role="direct",
                        )
                    )

        return sorted(candidates, key=lambda item: ((item.display_name or item.username).lower(), item.username.lower()))

    def _comment_mentions_principal(self, comment: TaskComment) -> bool:
        principal = self._user_session.principal if self._user_session is not None else None
        principal_user_id = str(getattr(principal, "user_id", "") or "").strip()
        mentioned_user_ids = {str(item).strip() for item in comment.mentioned_user_ids if str(item).strip()}
        if principal_user_id and principal_user_id in mentioned_user_ids:
            return True
        mentions = {item.lower() for item in comment.mentions}
        aliases = self._principal_aliases()
        return bool(aliases and not mentions.isdisjoint(aliases))

    def _comment_is_unread_for_principal(self, comment: TaskComment) -> bool:
        if not self._comment_mentions_principal(comment):
            return False
        principal = self._user_session.principal if self._user_session is not None else None
        principal_user_id = str(getattr(principal, "user_id", "") or "").strip()
        if principal_user_id:
            read_by_user_ids = {str(item).strip() for item in comment.read_by_user_ids if str(item).strip()}
            if principal_user_id in read_by_user_ids:
                return False
        aliases = self._principal_aliases()
        read_by = {item.lower() for item in comment.read_by}
        return read_by.isdisjoint(aliases)

    def _require_task(self, task_id: str):
        task = self._task_repo.get(task_id)
        if task is None:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        return task

    def _principal_aliases(self) -> set[str]:
        principal = self._user_session.principal if self._user_session is not None else None
        if principal is None:
            return set()
        aliases: set[str] = set()
        if principal.username:
            aliases.add(principal.username.strip().lower())
        display_name = (principal.display_name or "").strip().lower()
        if display_name:
            aliases.add(display_name.strip(" @"))
            aliases.add(display_name.replace(" ", "").strip(" @"))
            aliases.add(display_name.replace(" ", ".").strip(" @"))
        return {alias for alias in aliases if alias}

    def _principal_primary_alias(self) -> str:
        principal = self._user_session.principal if self._user_session is not None else None
        if principal is None or not getattr(principal, "username", None):
            return ""
        return str(principal.username).strip().lower()

    @staticmethod
    def _body_preview(body: str) -> str:
        text = " ".join((body or "").split())
        return text if len(text) <= 120 else f"{text[:117]}..."


__all__ = ["CollaborationService"]
