from __future__ import annotations

from datetime import UTC, datetime

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.collaboration.collaboration_events import (
    TaskCommentReactionChanged,
    TaskCommentReactionChangeType,
    TaskCommentReadStateChanged,
)
from src.core.modules.project_management.application.collaboration.dto.commands.comment_reactions import (
    TaskCollaborationReactionCommand,
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
from src.core.modules.project_management.domain.collaboration import TaskComment
from src.core.modules.project_management.domain.tasks.task import Task
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.common.pydantic import normalize_optional_text
from src.core.shared.audit import record_audit_entry


class CollaborationCommentEngagementHandler(ProjectManagementModuleGuardMixin):
    """Per-principal, read-level engagement with comments: idempotent emoji
    reactions and mention read-state. Requires only collaboration.read and no
    authorship, unlike the comment lifecycle handler."""

    def __init__(
        self,
        *,
        comment_repo: TaskCommentRepository,
        policy: CollaborationVisibilityPolicy,
        uow_factory: CollaborationUnitOfWorkFactory,
        tenant_context_service,
        user_session=None,
        module_catalog_service=None,
    ) -> None:
        self._comment_repo = comment_repo
        self._policy = policy
        self._uow_factory = uow_factory
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def _require_comment_for_reaction(
        self, comment_id: str
    ) -> tuple[TaskComment, Task]:
        comment = self._comment_repo.get(comment_id)
        if comment is None:
            raise NotFoundError(
                "Comment not found.", code="COLLABORATION_COMMENT_NOT_FOUND"
            )
        if comment.is_deleted:
            raise BusinessRuleError(
                "Cannot react to a deleted comment.",
                code="COLLABORATION_COMMENT_DELETED",
            )
        task = self._policy.require_task(comment.task_id)
        require_permission(
            self._user_session,
            "collaboration.read",
            operation_label="react to task collaboration update",
        )
        require_project_permission(
            self._user_session,
            task.project_id,
            "collaboration.read",
            operation_label="react to task collaboration update",
        )
        return comment, task

    def _principal_user_id_for_reaction(self) -> str:
        principal = self._policy.principal
        principal_user_id = str(getattr(principal, "user_id", "") or "").strip()
        if not principal_user_id:
            raise BusinessRuleError(
                "A signed-in user is required to react to comments.",
                code="COLLABORATION_REACTION_REQUIRES_USER",
            )
        return principal_user_id

    def react_to_comment(self, command: TaskCollaborationReactionCommand) -> TaskComment:
        comment_id = command.comment_id.strip()
        emoji = command.emoji
        comment, task = self._require_comment_for_reaction(comment_id)
        principal_user_id = self._principal_user_id_for_reaction()
        emoji_key = normalize_optional_text(emoji)
        if not emoji_key:
            raise ValidationError(
                "Reaction emoji is required.",
                code="COLLABORATION_REACTION_EMOJI_REQUIRED",
            )
        reactions = {key: list(value) for key, value in comment.reactions.items()}
        reactors = set(reactions.get(emoji_key, []))
        if principal_user_id in reactors:
            return comment
        reactors.add(principal_user_id)
        reactions[emoji_key] = sorted(reactors)
        comment.reactions = reactions
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="react to task collaboration update"
        )
        with self._uow_factory.create(context=new_collaboration_context()) as uow:
            uow.comments.update(comment)
            uow.record_event(
                TaskCommentReactionChanged(
                    tenant_id=scope.tenant_id,
                    organization_id=scope.organization_id,
                    project_id=task.project_id,
                    task_id=task.id,
                    comment_id=comment.id,
                    change_type=TaskCommentReactionChangeType.ADDED,
                    occurred_at=datetime.now(UTC),
                )
            )
            uow.commit()
        return comment

    def remove_reaction(self, command: TaskCollaborationReactionCommand) -> TaskComment:
        comment_id = command.comment_id.strip()
        emoji = command.emoji
        comment, task = self._require_comment_for_reaction(comment_id)
        principal_user_id = self._principal_user_id_for_reaction()
        emoji_key = normalize_optional_text(emoji)
        if not emoji_key:
            raise ValidationError(
                "Reaction emoji is required.",
                code="COLLABORATION_REACTION_EMOJI_REQUIRED",
            )
        reactions = {key: list(value) for key, value in comment.reactions.items()}
        reactors = set(reactions.get(emoji_key, []))
        if principal_user_id not in reactors:
            return comment
        reactors.discard(principal_user_id)
        if reactors:
            reactions[emoji_key] = sorted(reactors)
        else:
            reactions.pop(emoji_key, None)
        comment.reactions = reactions
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="remove reaction from task collaboration update"
        )
        with self._uow_factory.create(context=new_collaboration_context()) as uow:
            uow.comments.update(comment)
            uow.record_event(
                TaskCommentReactionChanged(
                    tenant_id=scope.tenant_id,
                    organization_id=scope.organization_id,
                    project_id=task.project_id,
                    task_id=task.id,
                    comment_id=comment.id,
                    change_type=TaskCommentReactionChangeType.REMOVED,
                    occurred_at=datetime.now(UTC),
                )
            )
            uow.commit()
        return comment

    def mark_task_mentions_read(self, task_id: str) -> None:
        task = self._policy.require_task(task_id)
        require_permission(
            self._user_session,
            "collaboration.read",
            operation_label="mark collaboration updates read",
        )
        require_project_permission(
            self._user_session,
            task.project_id,
            "collaboration.read",
            operation_label="mark collaboration updates read",
        )
        principal = self._policy.principal
        principal_user_id = str(getattr(principal, "user_id", "") or "").strip()
        aliases = self._policy.principal_aliases()
        if not principal_user_id and not aliases:
            return

        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="mark collaboration updates read"
        )
        with self._uow_factory.create(context=new_collaboration_context()) as uow:
            while True:
                batch = uow.comments.list_unread_mentions_for_task(
                    task_id,
                    user_id=principal_user_id,
                    aliases=tuple(sorted(aliases)),
                    limit=100,
                )
                if not batch:
                    break
                updated_in_batch = 0
                for comment in batch:
                    if not self._policy.comment_mentions_principal(comment):
                        continue

                    user_reads = {
                        str(item).strip()
                        for item in comment.read_by_user_ids
                        if str(item).strip()
                    }
                    alias_reads = {item.lower() for item in comment.read_by}
                    already_read = principal_user_id in user_reads or (
                        bool(aliases) and not alias_reads.isdisjoint(aliases)
                    )
                    if already_read:
                        continue

                    if principal_user_id:
                        comment.read_by_user_ids = sorted(
                            user_reads.union({principal_user_id})
                        )
                    primary_alias = self._policy.principal_primary_alias()
                    if primary_alias:
                        comment.read_by = sorted(alias_reads.union({primary_alias}))
                    uow.comments.update(comment)
                    updated_in_batch += 1
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
                        entity_parent_id=task_id,
                        metadata={
                            "action": "collaboration.comment.mark_read",
                            "task_id": task_id,
                        },
                        commit=False,
                        fail_closed=True,
                    )
                    uow.record_event(
                        TaskCommentReadStateChanged(
                            tenant_id=scope.tenant_id,
                            organization_id=scope.organization_id,
                            project_id=task.project_id,
                            task_id=task_id,
                            comment_id=comment.id,
                            occurred_at=datetime.now(UTC),
                        )
                    )
                if updated_in_batch == 0:
                    break
            uow.commit()


__all__ = ["CollaborationCommentEngagementHandler"]
