from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from src.core.modules.project_management.domain.collaboration import (
    TaskComment,
    normalize_task_comment_body,
    resolve_mentions,
)
from src.core.modules.project_management.infrastructure.collaboration_attachments import store_task_comment_attachments
from src.core.modules.project_management.access.scope_permissions import require_project_permission
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    OperationNotPermittedError,
    ValidationError,
)
from src.core.platform.common.pydantic import normalize_optional_text
from src.core.shared.events.domain_events import domain_events
from src.core.shared.notifications import safe_dispatch_notification


class CollaborationCommentCommandMixin:
    @staticmethod
    def _require_comment_revision(comment: TaskComment, expected_revision: int | None) -> None:
        if expected_revision is None:
            return
        if comment.version != int(expected_revision):
            raise ConcurrencyError(
                "This comment changed after it was loaded. Refresh the discussion and try again.",
                code="STALE_WRITE",
            )

    def post_comment(
        self,
        *,
        task_id: str,
        body: str,
        attachments: Iterable[str] | None = None,
        linked_document_ids: Iterable[str] | None = None,
        parent_comment_id: str | None = None,
    ) -> TaskComment:
        task = self._require_task(task_id)
        require_permission(self._user_session, "collaboration.manage", operation_label="post task collaboration update")
        require_project_permission(
            self._user_session,
            task.project_id,
            "collaboration.manage",
            operation_label="post task collaboration update",
        )
        parent_id = normalize_optional_text(parent_comment_id) or None
        if parent_id:
            parent = self._comment_repo.get(parent_id)
            if parent is None or parent.task_id != task_id:
                raise NotFoundError(
                    "The comment you are replying to could not be found on this task.",
                    code="COLLABORATION_PARENT_COMMENT_NOT_FOUND",
                )
        text = normalize_task_comment_body(body)
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
            parent_comment_id=parent_id,
        )
        comment.attachments = store_task_comment_attachments(
            task_id=task_id,
            comment_id=comment.id,
            attachments=list(attachments or []),
        )
        try:
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
        except Exception:
            self._session.rollback()
            raise
        self._link_existing_comment_documents(
            comment_id=comment.id,
            document_ids=normalized_linked_document_ids,
        )
        domain_events.collaboration_changed.emit(task_id)
        self._notify_mentioned_users(task=task, comment=comment, author_user_id=comment.author_user_id)
        return comment

    def _notify_mentioned_users(self, *, task, comment: TaskComment, author_user_id: str | None) -> None:
        snippet = comment.body if len(comment.body) <= 140 else f"{comment.body[:137]}..."
        task_name = getattr(task, "name", "") or task.id
        for user_id in comment.mentioned_user_ids:
            if not user_id or user_id == author_user_id:
                continue
            safe_dispatch_notification(
                self,
                recipient_user_id=user_id,
                category="pm.comment.mentioned.v1",
                title="You were mentioned in a comment",
                body=f'On "{task_name}": {snippet}',
                metadata={"task_id": task.id, "project_id": task.project_id, "comment_id": comment.id},
            )

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
        try:
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
        except Exception:
            self._session.rollback()
            raise
        if changed:
            domain_events.collaboration_changed.emit(task_id)

    def edit_comment(
        self,
        comment_id: str,
        body: str,
        *,
        expected_revision: int | None = None,
    ) -> TaskComment:
        comment = self._comment_repo.get(comment_id)
        if comment is None:
            raise NotFoundError("Comment not found.", code="COLLABORATION_COMMENT_NOT_FOUND")
        if comment.is_deleted:
            raise BusinessRuleError(
                "A deleted comment cannot be edited.", code="COLLABORATION_COMMENT_DELETED"
            )
        self._require_comment_revision(comment, expected_revision)
        task = self._require_task(comment.task_id)
        require_permission(self._user_session, "collaboration.manage", operation_label="edit task collaboration update")
        require_project_permission(
            self._user_session,
            task.project_id,
            "collaboration.manage",
            operation_label="edit task collaboration update",
        )
        principal = self._user_session.principal if self._user_session is not None else None
        principal_user_id = str(getattr(principal, "user_id", "") or "").strip()
        if not principal_user_id or comment.author_user_id != principal_user_id:
            raise OperationNotPermittedError(
                "You can only edit your own comments.", code="COLLABORATION_COMMENT_NOT_OWNER"
            )
        text = normalize_task_comment_body(body)
        mention_candidates = self._list_mention_candidates_for_project(task.project_id)
        mentions, mentioned_user_ids, unresolved = resolve_mentions(text=text, candidates=mention_candidates)
        if unresolved:
            preview = ", ".join(f"@{token}" for token in unresolved[:4])
            raise ValidationError(
                f"Unknown mention handle(s): {preview}. Mention project collaborators with access to this task.",
                code="COLLABORATION_MENTION_UNKNOWN",
            )
        comment.body = text
        comment.mentions = mentions
        comment.mentioned_user_ids = mentioned_user_ids
        comment.updated_at = datetime.now(timezone.utc)
        try:
            self._comment_repo.update(comment)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        domain_events.collaboration_changed.emit(task.id)
        return comment

    def delete_comment(
        self,
        comment_id: str,
        *,
        expected_revision: int | None = None,
        reason: str | None = None,
    ) -> TaskComment:
        comment = self._comment_repo.get(comment_id)
        if comment is None:
            raise NotFoundError("Comment not found.", code="COLLABORATION_COMMENT_NOT_FOUND")
        task = self._require_task(comment.task_id)
        require_permission(self._user_session, "collaboration.manage", operation_label="delete task collaboration update")
        require_project_permission(
            self._user_session,
            task.project_id,
            "collaboration.manage",
            operation_label="delete task collaboration update",
        )
        if not comment.is_deleted:
            self._require_comment_revision(comment, expected_revision)
            principal = self._user_session.principal if self._user_session is not None else None
            comment.deleted_at = datetime.now(timezone.utc)
            comment.deleted_by_user_id = getattr(principal, "user_id", None)
            comment.deletion_reason = reason
            try:
                self._comment_repo.update(comment)
                self._session.commit()
            except Exception:
                self._session.rollback()
                raise
            domain_events.collaboration_changed.emit(task.id)
        return comment

    def _require_comment_for_reaction(self, comment_id: str) -> tuple[TaskComment, object]:
        comment = self._comment_repo.get(comment_id)
        if comment is None:
            raise NotFoundError("Comment not found.", code="COLLABORATION_COMMENT_NOT_FOUND")
        if comment.is_deleted:
            raise BusinessRuleError(
                "Cannot react to a deleted comment.", code="COLLABORATION_COMMENT_DELETED"
            )
        task = self._require_task(comment.task_id)
        require_permission(self._user_session, "collaboration.read", operation_label="react to task collaboration update")
        require_project_permission(
            self._user_session,
            task.project_id,
            "collaboration.read",
            operation_label="react to task collaboration update",
        )
        return comment, task

    def _principal_user_id_for_reaction(self) -> str:
        principal = self._user_session.principal if self._user_session is not None else None
        principal_user_id = str(getattr(principal, "user_id", "") or "").strip()
        if not principal_user_id:
            raise BusinessRuleError(
                "A signed-in user is required to react to comments.",
                code="COLLABORATION_REACTION_REQUIRES_USER",
            )
        return principal_user_id

    def react_to_comment(self, comment_id: str, emoji: str) -> TaskComment:
        comment, task = self._require_comment_for_reaction(comment_id)
        principal_user_id = self._principal_user_id_for_reaction()
        emoji_key = normalize_optional_text(emoji)
        if not emoji_key:
            raise ValidationError("Reaction emoji is required.", code="COLLABORATION_REACTION_EMOJI_REQUIRED")
        reactions = {key: list(value) for key, value in comment.reactions.items()}
        reactors = set(reactions.get(emoji_key, []))
        reactors.add(principal_user_id)
        reactions[emoji_key] = sorted(reactors)
        comment.reactions = reactions
        try:
            self._comment_repo.update(comment)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        domain_events.collaboration_changed.emit(task.id)
        return comment

    def remove_reaction(self, comment_id: str, emoji: str) -> TaskComment:
        comment, task = self._require_comment_for_reaction(comment_id)
        principal_user_id = self._principal_user_id_for_reaction()
        emoji_key = normalize_optional_text(emoji)
        if not emoji_key:
            raise ValidationError("Reaction emoji is required.", code="COLLABORATION_REACTION_EMOJI_REQUIRED")
        reactions = {key: list(value) for key, value in comment.reactions.items()}
        reactors = set(reactions.get(emoji_key, []))
        reactors.discard(principal_user_id)
        if reactors:
            reactions[emoji_key] = sorted(reactors)
        else:
            reactions.pop(emoji_key, None)
        comment.reactions = reactions
        try:
            self._comment_repo.update(comment)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        domain_events.collaboration_changed.emit(task.id)
        return comment


__all__ = ["CollaborationCommentCommandMixin"]
