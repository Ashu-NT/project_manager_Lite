from __future__ import annotations

from src.core.modules.project_management.application.resources.resource_capability_events import (
    ResourceCapabilityChanged,
)
from src.core.modules.project_management.application.resources.resource_master_events import (
    ResourceMasterChanged,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    OrganizationScope,
    ResourceScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

RESOURCE_CATEGORY = "resource"
RESOURCE_LIST_SCOPE_CODE = "resource_list"
RESOURCE_CAPABILITIES_SCOPE_CODE = "resource_capabilities"
RESOURCE_MODULE_CODE = "project_management"
RESOURCE_ENTITY_TYPE = "resource"


def _organization_scope_target(scope_code: str, scope: OrganizationScope) -> tuple[str, str, str]:
    """The dedupe identity IS the (scope_code, target/scope) identity -- never a raw event
    field. `OrganizationScope` carries no per-resource identity, so two different resources
    changing within one transaction are, correctly, the same target: the org-wide list."""
    return (scope_code, scope.tenant_id, scope.organization_id)


def _resource_scope_target(scope_code: str, scope: ResourceScope) -> tuple[str, str, str, str, str, str]:
    """`ResourceScope` carries exact-resource identity, so the dedupe target legitimately
    includes it -- two different resources are two different targets."""
    return (
        scope_code,
        scope.tenant_id,
        scope.organization_id,
        scope.module_code,
        scope.entity_type,
        scope.entity_id,
    )


def build_resource_list_view_invalidation_handler(channel: ViewInvalidationChannel):

    current_correlation_id: list[str | None] = [None]
    notified_targets: set[tuple[str, str, str]] = set()

    def handle_resource_master_event(
        event: ResourceMasterChanged, context: DomainEventContext
    ) -> None:
        if context.correlation_id != current_correlation_id[0]:
            current_correlation_id[0] = context.correlation_id
            notified_targets.clear()

        scope = OrganizationScope(event.tenant_id, event.organization_id)
        target = _organization_scope_target(RESOURCE_LIST_SCOPE_CODE, scope)
        if target in notified_targets:
            return
        notified_targets.add(target)

        channel.notify(
            ViewInvalidationHint(
                scope=scope,
                category=RESOURCE_CATEGORY,
                scope_code=RESOURCE_LIST_SCOPE_CODE,
                entity_type=RESOURCE_ENTITY_TYPE,
                entity_id=event.resource_id,
            )
        )

    return handle_resource_master_event


def build_resource_capabilities_view_invalidation_handler(channel: ViewInvalidationChannel):
    """`resource_capabilities` is exact-resource (`ResourceScope`) -- its dedupe target identity
    includes the resource itself, so the same resource repeated within one transaction collapses
    to one hint, but two distinct resources' capability changes within the same transaction
    still produce two hints (two genuinely different targets)."""

    current_correlation_id: list[str | None] = [None]
    notified_targets: set[tuple[str, str, str, str, str, str]] = set()

    def handle_resource_capability_event(
        event: ResourceCapabilityChanged, context: DomainEventContext
    ) -> None:
        if context.correlation_id != current_correlation_id[0]:
            current_correlation_id[0] = context.correlation_id
            notified_targets.clear()

        scope = ResourceScope(
            tenant_id=event.tenant_id,
            organization_id=event.organization_id,
            module_code=RESOURCE_MODULE_CODE,
            entity_type=RESOURCE_ENTITY_TYPE,
            entity_id=event.resource_id,
        )
        target = _resource_scope_target(RESOURCE_CAPABILITIES_SCOPE_CODE, scope)
        if target in notified_targets:
            return
        notified_targets.add(target)

        channel.notify(
            ViewInvalidationHint(
                scope=scope,
                category=RESOURCE_CATEGORY,
                scope_code=RESOURCE_CAPABILITIES_SCOPE_CODE,
                entity_type=RESOURCE_ENTITY_TYPE,
                entity_id=event.resource_id,
            )
        )

    return handle_resource_capability_event


__all__ = [
    "build_resource_list_view_invalidation_handler",
    "build_resource_capabilities_view_invalidation_handler",
    "RESOURCE_CATEGORY",
    "RESOURCE_LIST_SCOPE_CODE",
    "RESOURCE_CAPABILITIES_SCOPE_CODE",
    "RESOURCE_MODULE_CODE",
    "RESOURCE_ENTITY_TYPE",
]
