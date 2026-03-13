from __future__ import annotations

import re
from typing import Iterable

from sqlalchemy.orm import Session

from core.events.domain_events import domain_events
from core.exceptions import NotFoundError, ValidationError
from core.interfaces import ProjectRepository, TaskCommentRepository, TaskRepository
from core.models import CollaborationInboxItem, TaskComment
from core.services.access.authorization import require_project_permission
from core.services.auth.authorization import require_permission

_MENTION_RE = re.compile(r"@([A-Za-z0-9_.-]+)")


class CollaborationService:
    def __init__(
        self,
        *,
        session: Session,
        comment_repo: TaskCommentRepository,
        task_repo: TaskRepository,
        project_repo: ProjectRepository,
        user_session=None,
    ) -> None:
        self._session = session
        self._comment_repo = comment_repo
        self._task_repo = task_repo
        self._project_repo = project_repo
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
        principal = self._user_session.principal if self._user_session is not None else None
        comment = TaskComment.create(
            task_id=task_id,
            author_user_id=getattr(principal, "user_id", None),
            author_username=getattr(principal, "username", None) or "unknown",
            body=text,
            mentions=sorted({match.lower() for match in _MENTION_RE.findall(text)}),
            attachments=attachments or [],
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
        aliases = self._principal_aliases()
        if not aliases:
            return
        changed = False
        for comment in self._comment_repo.list_by_task(task_id):
            mentions = {item.lower() for item in comment.mentions}
            if mentions.isdisjoint(aliases):
                continue
            read_by = {item.lower() for item in comment.read_by}
            if not read_by.isdisjoint(aliases):
                continue
            comment.read_by = sorted(read_by.union(aliases))
            self._comment_repo.update(comment)
            changed = True
        if changed:
            self._session.commit()
            domain_events.collaboration_changed.emit(task_id)

    def unread_mentions_count(self) -> int:
        return sum(1 for item in self.list_inbox(limit=500) if item.unread)

    def list_inbox(self, *, limit: int = 200) -> list[CollaborationInboxItem]:
        require_permission(self._user_session, "collaboration.read", operation_label="view collaboration inbox")
        aliases = self._principal_aliases()
        comments = self._list_accessible_comments(limit=limit)
        items: list[CollaborationInboxItem] = []
        for comment in comments:
            mentions = {item.lower() for item in comment.mentions}
            if mentions.isdisjoint(aliases):
                continue
            read_by = {item.lower() for item in comment.read_by}
            unread = read_by.isdisjoint(aliases)
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
                    unread=unread,
                )
            )
        return sorted(items, key=lambda item: item.created_at, reverse=True)[:limit]

    def list_recent_activity(self, *, limit: int = 200) -> list[CollaborationInboxItem]:
        require_permission(self._user_session, "collaboration.read", operation_label="view collaboration activity")
        aliases = self._principal_aliases()
        items: list[CollaborationInboxItem] = []
        for comment in self._list_accessible_comments(limit=limit):
            task = self._task_repo.get(comment.task_id)
            if task is None:
                continue
            project = self._project_repo.get(task.project_id)
            if project is None:
                continue
            mentions = [item.lower() for item in comment.mentions]
            read_by = {item.lower() for item in comment.read_by}
            unread = bool(set(mentions).intersection(aliases) and read_by.isdisjoint(aliases))
            items.append(
                CollaborationInboxItem(
                    comment_id=comment.id,
                    task_id=task.id,
                    task_name=task.name,
                    project_id=project.id,
                    project_name=project.name,
                    author_username=comment.author_username or "unknown",
                    body_preview=self._body_preview(comment.body),
                    mentions=mentions,
                    created_at=comment.created_at,
                    unread=unread,
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

    @staticmethod
    def _body_preview(body: str) -> str:
        text = " ".join((body or "").split())
        return text if len(text) <= 120 else f"{text[:117]}..."


__all__ = ["CollaborationService"]
