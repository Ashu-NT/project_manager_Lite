from __future__ import annotations

from src.core.modules.project_management.application.collaboration.collaboration_events import (
    TaskCommentChanged,
    TaskCommentReactionChanged,
    TaskCommentReadStateChanged,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    OrganizationScope,
    ResourceScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

TASK_PRESENCE_CATEGORY = "collaboration_presence"
TASK_PRESENCE_SCOPE_CODE = "task_presence"
TASK_PRESENCE_MODULE_CODE = "project_management"
TASK_PRESENCE_ENTITY_TYPE = "task"


def notify_task_presence_stale(
    channel: ViewInvalidationChannel | None,
    *,
    tenant_id: str | None,
    organization_id: str,
    task_id: str,
) -> None:
    """Presence is transient coordination state, not a business fact -- there is no
    `PresenceDomainEvent`, no `uow.record_event(...)`, no transactional/post-commit dispatch. A
    `TaskPresence` row is nonetheless a real, TTL-windowed read model (`list_task_presence`), so a
    plain, direct, synchronous `ViewInvalidationHint` notify (skipping the DomainEvent pipeline
    entirely) is the correct, lightweight transport -- not an abuse of ViewInvalidation, since a
    genuine read-model projection did just become stale."""
    if channel is None:
        return
    channel.notify(
        ViewInvalidationHint(
            scope=ResourceScope(
                tenant_id=tenant_id,
                organization_id=organization_id,
                module_code=TASK_PRESENCE_MODULE_CODE,
                entity_type=TASK_PRESENCE_ENTITY_TYPE,
                entity_id=task_id,
            ),
            category=TASK_PRESENCE_CATEGORY,
            scope_code=TASK_PRESENCE_SCOPE_CODE,
            entity_type=TASK_PRESENCE_ENTITY_TYPE,
            entity_id=task_id,
        )
    )


TASK_COMMENT_CATEGORY = "collaboration_comment"
TASK_COMMENT_SCOPE_CODE = "task_comments"
COLLABORATION_WORKSPACE_SCOPE_CODE = "collaboration_workspace"
COLLABORATION_MODULE_CODE = "project_management"
TASK_COMMENT_ENTITY_TYPE = "task"

_TaskCommentEvent = TaskCommentChanged | TaskCommentReactionChanged | TaskCommentReadStateChanged

_OrgTarget = tuple[str, str, str]
_TaskTarget = tuple[str, str, str, str, str, str]


def _organization_scope_target(scope_code: str, scope: OrganizationScope) -> _OrgTarget:
    return (scope_code, scope.tenant_id, scope.organization_id)


def _task_scope_target(scope_code: str, scope: ResourceScope) -> _TaskTarget:
    return (
        scope_code,
        scope.tenant_id,
        scope.organization_id,
        scope.module_code,
        scope.entity_type,
        scope.entity_id,
    )


def build_task_comment_view_invalidation_handler(channel: ViewInvalidationChannel):
    """`TaskCommentChanged`/`TaskCommentReactionChanged`/`TaskCommentReadStateChanged` all stale
    the exact task's own comment list; only `TaskCommentChanged` (a comment was created, edited,
    or removed -- content that genuinely appears in cross-project "recent activity") additionally
    stales the organization-wide Collaboration workspace/dashboard activity target. Reactions and
    read-receipts are deliberately narrower -- no current consumer displays reaction summaries or
    unread counts at the workspace level, so broadcasting them org-wide would be unproven,
    wasteful fan-out (brief's own "do not map every event to every target without proof")."""

    current_correlation_id: list[str | None] = [None]
    notified_task_targets: set[_TaskTarget] = set()
    notified_org_targets: set[_OrgTarget] = set()

    def handle_task_comment_event(
        event: _TaskCommentEvent,
        context: DomainEventContext,
    ) -> None:
        if context.correlation_id != current_correlation_id[0]:
            current_correlation_id[0] = context.correlation_id
            notified_task_targets.clear()
            notified_org_targets.clear()

        task_scope = ResourceScope(
            tenant_id=event.tenant_id,
            organization_id=event.organization_id,
            module_code=COLLABORATION_MODULE_CODE,
            entity_type=TASK_COMMENT_ENTITY_TYPE,
            entity_id=event.task_id,
        )
        task_target = _task_scope_target(TASK_COMMENT_SCOPE_CODE, task_scope)
        if task_target not in notified_task_targets:
            notified_task_targets.add(task_target)
            channel.notify(
                ViewInvalidationHint(
                    scope=task_scope,
                    category=TASK_COMMENT_CATEGORY,
                    scope_code=TASK_COMMENT_SCOPE_CODE,
                    entity_type=TASK_COMMENT_ENTITY_TYPE,
                    entity_id=event.task_id,
                )
            )

        if not isinstance(event, TaskCommentChanged):
            return

        org_scope = OrganizationScope(event.tenant_id, event.organization_id)
        org_target = _organization_scope_target(COLLABORATION_WORKSPACE_SCOPE_CODE, org_scope)
        if org_target not in notified_org_targets:
            notified_org_targets.add(org_target)
            channel.notify(
                ViewInvalidationHint(
                    scope=org_scope,
                    category=TASK_COMMENT_CATEGORY,
                    scope_code=COLLABORATION_WORKSPACE_SCOPE_CODE,
                    entity_type=TASK_COMMENT_ENTITY_TYPE,
                    entity_id=event.task_id,
                )
            )

    return handle_task_comment_event


__all__ = [
    "notify_task_presence_stale",
    "TASK_PRESENCE_CATEGORY",
    "TASK_PRESENCE_SCOPE_CODE",
    "TASK_PRESENCE_MODULE_CODE",
    "TASK_PRESENCE_ENTITY_TYPE",
    "build_task_comment_view_invalidation_handler",
    "TASK_COMMENT_CATEGORY",
    "TASK_COMMENT_SCOPE_CODE",
    "COLLABORATION_WORKSPACE_SCOPE_CODE",
    "COLLABORATION_MODULE_CODE",
    "TASK_COMMENT_ENTITY_TYPE",
]
