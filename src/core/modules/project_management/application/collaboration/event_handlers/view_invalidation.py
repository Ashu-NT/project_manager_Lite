from __future__ import annotations

from src.core.shared.events.view_invalidation import (
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


__all__ = [
    "notify_task_presence_stale",
    "TASK_PRESENCE_CATEGORY",
    "TASK_PRESENCE_SCOPE_CODE",
    "TASK_PRESENCE_MODULE_CODE",
    "TASK_PRESENCE_ENTITY_TYPE",
]
