from __future__ import annotations

from src.core.platform.domain.security.authorization.roles.events import (
    RoleBindingAssigned,
    RoleBindingRevoked,
)
from src.core.platform.domain.security.authorization.roles.role_binding_scope import (
    RoleBindingResourceScope,
    RoleBindingScope,
    RoleBindingTenantScope,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    EventScope,
    OrganizationScope,
    PlatformScope,
    TenantScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

ROLE_BINDING_CATEGORY = "role_binding"
ROLE_BINDING_ASSIGNMENTS_SCOPE_CODE = "role_binding_assignments"

_RoleBindingEvent = RoleBindingAssigned | RoleBindingRevoked


def _to_event_scope(scope: RoleBindingScope) -> EventScope:
    if isinstance(scope, RoleBindingResourceScope):
        if scope.organization_id:
            return OrganizationScope(scope.tenant_id, scope.organization_id)
        return TenantScope(scope.tenant_id)
    if isinstance(scope, RoleBindingTenantScope):
        return TenantScope(scope.tenant_id)
    return PlatformScope()


def build_role_binding_view_invalidation_handler(channel: ViewInvalidationChannel):
    """Returns one `PostCommitEventHandler` bound to `channel`, reused for explicit
    composition-root registration against both RoleBinding events
    (`post_commit_bus.subscribe(RoleBindingAssigned, handler)`,
    `subscribe(RoleBindingRevoked, handler)`)."""

    def handle_role_binding_event(event: _RoleBindingEvent, context: DomainEventContext) -> None:
        channel.notify(
            ViewInvalidationHint(
                scope=_to_event_scope(event.scope),
                category=ROLE_BINDING_CATEGORY,
                scope_code=ROLE_BINDING_ASSIGNMENTS_SCOPE_CODE,
                entity_type="role_binding",
                entity_id=event.binding_id,
            )
        )

    return handle_role_binding_event


__all__ = [
    "build_role_binding_view_invalidation_handler",
    "ROLE_BINDING_CATEGORY",
    "ROLE_BINDING_ASSIGNMENTS_SCOPE_CODE",
]
