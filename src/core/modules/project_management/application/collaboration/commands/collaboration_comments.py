from __future__ import annotations

import json
import logging
from collections.abc import Callable, Iterable
from contextlib import contextmanager
from datetime import UTC, datetime
from hashlib import sha256
from typing import cast

from sqlalchemy.exc import IntegrityError

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.collaboration.collaboration_events import (
    TaskCommentChanged,
    TaskCommentChangeType,
)
from src.core.modules.project_management.application.collaboration.utils.visibility import (
    CollaborationVisibilityPolicy,
    new_collaboration_context,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.contracts.repositories.collaboration.collaboration import (
    TaskCommentRepository,
)
from src.core.modules.project_management.contracts.uow.collaboration.collaboration_unit_of_work import (
    CollaborationUnitOfWorkFactory,
)
from src.core.modules.project_management.domain.collaboration import (
    TaskComment,
    extract_mention_tokens,
    normalize_task_comment_body,
    resolve_mentions,
)
from src.core.platform.application.master_data.documents.commands.document_attachment_commands import (
    link_existing_document_in_uow,
    register_entity_attachments_in_uow,
)
from src.core.platform.application.master_data.documents.document_access import (
    attachment_visibility,
)
from src.core.platform.application.master_data.documents.document_context import (
    active_organization,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    ConfigurationError,
    NotFoundError,
    OperationNotPermittedError,
    ValidationError,
)
from src.core.platform.common.pydantic import normalize_optional_text
from src.core.platform.contract.port.master_data.documents.document_access_policy import (
    DocumentAccessPolicy,
)
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry
from src.core.shared.time.clock import Clock

logger = logging.getLogger(__name__)


class CollaborationCommentCommandHandler(ProjectManagementModuleGuardMixin):
    """Governed comment lifecycle writes: post (mention resolution, idempotent
    submission replay, attachment storage/compensation, shared-document links),
    author-owned edit and soft-delete guarded by the optimistic revision. One
    collaboration UoW per operation."""

    def __init__(
        self,
        *,
        comment_repo: TaskCommentRepository,
        policy: CollaborationVisibilityPolicy,
        uow_factory: CollaborationUnitOfWorkFactory,
        tenant_context_service,
        user_session=None,
        module_catalog_service=None,
        document_access_policy: DocumentAccessPolicy | None = None,
        attachment_store: Callable[..., list[str]] | None = None,
        attachment_cleanup: Callable[[list[str]], None] | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._comment_repo = comment_repo
        self._policy = policy
        self._uow_factory = uow_factory
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service
        self._document_access_policy = document_access_policy
        self._attachment_store = attachment_store
        self._attachment_cleanup = attachment_cleanup
        self._clock = clock

    def _normalize_linked_document_ids(self, linked_document_ids: Iterable[str] | None) -> list[str]:
        normalized = list(
            dict.fromkeys(str(item).strip() for item in (linked_document_ids or []) if str(item).strip())
        )
        if normalized and self._document_access_policy is None:
            raise ValidationError(
                "Shared document linking is not available in the current collaboration runtime.",
                code="COLLABORATION_DOCUMENT_LIBRARY_UNAVAILABLE",
            )
        return normalized

    @contextmanager
    def _compensate_uncommitted_attachments(self, paths: list[str]):
        state = {"uow": None}
        try:
            yield state
        except BaseException:
            if paths and self._attachment_cleanup is not None and not getattr(state["uow"], "committed", False):
                try:
                    self._attachment_cleanup(paths)
                except Exception:
                    logger.exception("Failed to compensate uncommitted task comment attachments")
            raise

    def post_comment(
        self,
        *,
        task_id: str,
        body: str,
        attachments: Iterable[str] | None = None,
        linked_document_ids: Iterable[str] | None = None,
        parent_comment_id: str | None = None,
        submission_id: str | None = None,
    ) -> TaskComment:
        task = self._policy.require_task(task_id)
        require_permission(
            self._user_session,
            "collaboration.manage",
            operation_label="post task collaboration update",
        )
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
            if parent.is_deleted:
                raise BusinessRuleError(
                    "Cannot reply to a deleted comment.",
                    code="COLLABORATION_PARENT_COMMENT_DELETED",
                )
        text = normalize_task_comment_body(body)
        principal = self._policy.principal
        principal_user_id = str(getattr(principal, "user_id", "") or "").strip()
        normalized_linked_document_ids = self._normalize_linked_document_ids(
            linked_document_ids
        )
        attachment_paths = [str(path).strip() for path in (attachments or []) if str(path).strip()]
        normalized_submission_id = (
            normalize_optional_text(submission_id) if submission_id is not None else None
        )
        if submission_id is not None and (
            not normalized_submission_id or len(normalized_submission_id) > 128
        ):
            raise ValidationError(
                "Comment submission ID is invalid.", code="COLLABORATION_SUBMISSION_ID_INVALID"
            )
        submission_hash = sha256(
            json.dumps(
                [task_id, principal_user_id, parent_id, text, attachment_paths,
                 normalized_linked_document_ids],
                ensure_ascii=True, separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        if normalized_submission_id:
            existing = self._comment_repo.get(normalized_submission_id)
            if existing is not None:
                if (
                    existing.task_id == task_id
                    and existing.author_user_id == principal_user_id
                    and existing.submission_hash == submission_hash
                ):
                    return existing
                raise ValidationError(
                    "This comment submission ID was already used for different content.",
                    code="COLLABORATION_SUBMISSION_CONFLICT",
                )
        mentions, mentioned_user_ids, unresolved = (
            resolve_mentions(
                text=text,
                candidates=self._policy.mention_candidates_for_text(task.project_id, text),
            )
            if extract_mention_tokens(text) else ([], [], [])
        )
        if unresolved:
            preview = ", ".join(f"@{token}" for token in unresolved[:4])
            raise ValidationError(
                f"Unknown mention handle(s): {preview}. Mention project collaborators with access to this task.",
                code="COLLABORATION_MENTION_UNKNOWN",
            )
        comment = TaskComment.create(
            task_id=task_id,
            author_user_id=getattr(principal, "user_id", None),
            author_username=getattr(principal, "username", None) or "unknown",
            body=text,
            mentions=mentions,
            mentioned_user_ids=mentioned_user_ids,
            attachments=[],
            parent_comment_id=parent_id,
            submission_id=normalized_submission_id,
            submission_hash=submission_hash,
        )
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="post task collaboration update"
        )
        if attachment_paths:
            if self._attachment_store is None or self._attachment_cleanup is None:
                raise ConfigurationError(
                    "Collaboration attachment storage is not configured."
                )
            comment.attachments = self._attachment_store(
                task_id=task_id,
                comment_id=comment.id,
                attachments=attachment_paths,
            )
        uploader_user_id = getattr(principal, "user_id", None)

        with self._compensate_uncommitted_attachments(comment.attachments) as attachment_state, self._uow_factory.create(context=new_collaboration_context()) as uow:
            attachment_state["uow"] = uow
            if parent_id:
                locked_parent = uow.comments.get_for_reply(parent_id)
                if locked_parent is None or locked_parent.task_id != task_id:
                    raise NotFoundError(
                        "The comment you are replying to could not be found on this task.",
                        code="COLLABORATION_PARENT_COMMENT_NOT_FOUND",
                    )
                if locked_parent.is_deleted:
                    raise BusinessRuleError(
                        "Cannot reply to a deleted comment.",
                        code="COLLABORATION_PARENT_COMMENT_DELETED",
                    )
            uow.comments.add(comment)
            record_audit_entry(
                uow,
                operation="create",
                entity_type="task_comment",
                entity_id=comment.id,
                module="project_management",
                organization_id=scope.organization_id,
                category="MASTER_DATA",
                severity="low",
                workspace_id=task.project_id,
                entity_parent_id=task_id,
                metadata={"action": "collaboration.comment.create", "task_id": task_id},
                commit=False,
                fail_closed=True,
            )
            record_activity(
                uow,
                action="collaboration.comment.create",
                entity_type="task_comment",
                entity_id=comment.id,
                module="project_management",
                workspace_id=task.project_id,
                parent_entity_id=task_id,
                details={"task_id": task_id},
                commit=False,
            )
            uow.record_event(
                TaskCommentChanged(
                    tenant_id=scope.tenant_id,
                    organization_id=scope.organization_id,
                    project_id=task.project_id,
                    task_id=task_id,
                    comment_id=comment.id,
                    change_type=TaskCommentChangeType.CREATED,
                    occurred_at=datetime.now(UTC),
                )
            )
            if self._document_access_policy is not None and comment.attachments:
                register_entity_attachments_in_uow(
                    uow=uow,
                    organization=active_organization(self._tenant_context_service),
                    module_code="project_management",
                    entity_type="task_comment",
                    entity_id=comment.id,
                    attachments=comment.attachments,
                    clock=cast(Clock, self._clock),
                    source_system="project_management",
                    uploaded_by_user_id=uploader_user_id,
                )
            if self._document_access_policy is not None and normalized_linked_document_ids:
                organization = active_organization(self._tenant_context_service)
                visibility = attachment_visibility(self._document_access_policy.visibility())
                for document_id in normalized_linked_document_ids:
                    link_existing_document_in_uow(
                        uow=uow,
                        organization=organization,
                        module_code="project_management",
                        entity_type="task_comment",
                        entity_id=comment.id,
                        document_id=document_id,
                        clock=cast(Clock, self._clock),
                        visibility=visibility,
                        link_role="reference",
                    )
            try:
                uow.commit()
            except IntegrityError:
                if normalized_submission_id:
                    existing = self._comment_repo.get(normalized_submission_id)
                    if (
                        existing is not None
                        and existing.task_id == task_id
                        and existing.author_user_id == principal_user_id
                        and existing.submission_hash == submission_hash
                    ):
                        if comment.attachments and self._attachment_cleanup is not None:
                            self._attachment_cleanup(comment.attachments)
                        return existing
                raise
        return comment

    @staticmethod
    def _require_comment_revision(
        comment: TaskComment, expected_revision: int | None
    ) -> None:
        if expected_revision is None:
            raise ValidationError(
                "The current comment revision is required. Refresh the discussion and try again.",
                code="COLLABORATION_COMMENT_REVISION_REQUIRED",
            )
        if comment.version != int(expected_revision):
            raise ConcurrencyError(
                "This comment changed after it was loaded. Refresh the discussion and try again.",
                code="STALE_WRITE",
            )

    def edit_comment(
        self,
        comment_id: str,
        body: str,
        *,
        expected_revision: int | None = None,
    ) -> TaskComment:
        comment = self._comment_repo.get(comment_id)
        if comment is None:
            raise NotFoundError(
                "Comment not found.", code="COLLABORATION_COMMENT_NOT_FOUND"
            )
        task = self._policy.require_task(comment.task_id)
        require_permission(
            self._user_session,
            "collaboration.manage",
            operation_label="edit task collaboration update",
        )
        require_project_permission(
            self._user_session,
            task.project_id,
            "collaboration.manage",
            operation_label="edit task collaboration update",
        )
        principal = self._policy.principal
        principal_user_id = str(getattr(principal, "user_id", "") or "").strip()
        if not principal_user_id or comment.author_user_id != principal_user_id:
            raise OperationNotPermittedError(
                "You can only edit your own comments.",
                code="COLLABORATION_COMMENT_NOT_OWNER",
            )
        if comment.is_deleted:
            raise BusinessRuleError(
                "A deleted comment cannot be edited.",
                code="COLLABORATION_COMMENT_DELETED",
            )
        self._require_comment_revision(comment, expected_revision)
        text = normalize_task_comment_body(body)
        mentions, mentioned_user_ids, unresolved = (
            resolve_mentions(
                text=text,
                candidates=self._policy.mention_candidates_for_text(task.project_id, text),
            )
            if extract_mention_tokens(text) else ([], [], [])
        )
        if unresolved:
            preview = ", ".join(f"@{token}" for token in unresolved[:4])
            raise ValidationError(
                f"Unknown mention handle(s): {preview}. Mention project collaborators with access to this task.",
                code="COLLABORATION_MENTION_UNKNOWN",
            )
        comment.body = text
        comment.mentions = mentions
        comment.mentioned_user_ids = mentioned_user_ids
        comment.updated_at = datetime.now(UTC)
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="edit task collaboration update"
        )
        with self._uow_factory.create(context=new_collaboration_context()) as uow:
            uow.comments.update(comment)
            record_audit_entry(
                uow,
                operation="update",
                entity_type="task_comment",
                entity_id=comment.id,
                module="project_management",
                organization_id=scope.organization_id,
                category="MASTER_DATA",
                severity="low",
                workspace_id=task.project_id,
                entity_parent_id=task.id,
                metadata={"action": "collaboration.comment.edit", "task_id": task.id},
                commit=False,
                fail_closed=True,
            )
            record_activity(
                uow,
                action="collaboration.comment.edit",
                entity_type="task_comment",
                entity_id=comment.id,
                module="project_management",
                workspace_id=task.project_id,
                parent_entity_id=task.id,
                details={"task_id": task.id},
                commit=False,
            )
            uow.record_event(
                TaskCommentChanged(
                    tenant_id=scope.tenant_id,
                    organization_id=scope.organization_id,
                    project_id=task.project_id,
                    task_id=task.id,
                    comment_id=comment.id,
                    change_type=TaskCommentChangeType.EDITED,
                    occurred_at=datetime.now(UTC),
                )
            )
            uow.commit()
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
            raise NotFoundError(
                "Comment not found.", code="COLLABORATION_COMMENT_NOT_FOUND"
            )
        task = self._policy.require_task(comment.task_id)
        require_permission(
            self._user_session,
            "collaboration.manage",
            operation_label="delete task collaboration update",
        )
        require_project_permission(
            self._user_session,
            task.project_id,
            "collaboration.manage",
            operation_label="delete task collaboration update",
        )
        if not comment.is_deleted:
            self._require_comment_revision(comment, expected_revision)
            principal = self._policy.principal
            comment.deleted_at = datetime.now(UTC)
            comment.deleted_by_user_id = getattr(principal, "user_id", None)
            comment.deletion_reason = reason
            scope = self._tenant_context_service.require_active_scope_ids(
                operation_label="delete task collaboration update"
            )
            with self._uow_factory.create(context=new_collaboration_context()) as uow:
                uow.comments.update(comment)
                record_audit_entry(
                    uow,
                    operation="delete",
                    entity_type="task_comment",
                    entity_id=comment.id,
                    module="project_management",
                    organization_id=scope.organization_id,
                    category="MASTER_DATA",
                    severity="low",
                    workspace_id=task.project_id,
                    entity_parent_id=task.id,
                    metadata={
                        "action": "collaboration.comment.delete",
                        "task_id": task.id,
                    },
                    commit=False,
                    fail_closed=True,
                )
                record_activity(
                    uow,
                    action="collaboration.comment.delete",
                    entity_type="task_comment",
                    entity_id=comment.id,
                    module="project_management",
                    workspace_id=task.project_id,
                    parent_entity_id=task.id,
                    details={"task_id": task.id},
                    commit=False,
                )
                uow.record_event(
                    TaskCommentChanged(
                        tenant_id=scope.tenant_id,
                        organization_id=scope.organization_id,
                        project_id=task.project_id,
                        task_id=task.id,
                        comment_id=comment.id,
                        change_type=TaskCommentChangeType.REMOVED,
                        occurred_at=datetime.now(UTC),
                    )
                )
                uow.commit()
        return comment


__all__ = ["CollaborationCommentCommandHandler"]
