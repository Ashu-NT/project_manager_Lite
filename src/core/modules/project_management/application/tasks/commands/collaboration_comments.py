from __future__ import annotations

from typing import Iterable

from src.src.core.modules.project_management.domain.collaboration import TaskComment
from src.core.modules.project_management.infrastructure.collaboration_attachments import store_task_comment_attachments
from src.core.modules.project_management.application.tasks.collaboration_mentions import resolve_mentions
from src.core.platform.access.authorization import require_project_permission
from src.core.platform.auth.authorization import require_permission
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.notifications.domain_events import domain_events


class CollaborationCommentCommandMixin:
    def post_comment(
        self,
        *,
        task_id: str,
        body: str,
        attachments: Iterable[str] | None = None,
        linked_document_ids: Iterable[str] | None = None,
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
        mentions, mentioned_user_ids, unresolved = resolve_mentions(text=text, candidates=mention_candidates)
        if unresolved:
            preview = ", ".join(f"@{token}" for token in unresolved[:4])
            raise ValidationError(
                f"Unknown mention handle(s): {preview}. Mention project collaborators with access to this task.",
                code="COLLABORATION_MENTION_UNKNOWN",
            )
        principal = self._user_session.principal if self._user_session is not None else None
        normalized_linked_document_ids = self._normalize_linked_document_ids(linked_document_ids)
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
        if self._document_integration_service is not None and comment.attachments:
            self._document_integration_service.register_entity_attachments(
                required_permission="collaboration.manage",
                operation_label="register task collaboration attachments",
                module_code="project_management",
                entity_type="task_comment",
                entity_id=comment.id,
                attachments=comment.attachments,
                source_system="project_management",
            )
        else:
            self._session.commit()
        self._link_existing_comment_documents(
            comment_id=comment.id,
            document_ids=normalized_linked_document_ids,
        )
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


__all__ = ["CollaborationCommentCommandMixin"]


