from __future__ import annotations

from src.core.platform.domain.security.auth.events import (
    CustomRoleCreated,
    CustomRoleRetired,
    CustomRoleUpdated,
    RolePolicyReconciled,
)
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

AUTHORIZATION_CONTEXT_CATEGORY = "authorization_context"
AUTHORIZATION_CONTEXT_SCOPE_CODE = "authorization_context"

_AuthorizationContextEvent = (
    CustomRoleCreated | CustomRoleUpdated | CustomRoleRetired | RolePolicyReconciled
)

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


def build_authorization_context_view_invalidation_handler(channel: ViewInvalidationChannel):
    """One `PostCommitEventHandler` bound to `channel`, registered against the four Role-owned
    facts (`CustomRoleCreated`/`Updated`/`Retired`, `RolePolicyReconciled`) -- the
    `authorization_context` target's own share of the durable event families it maps to (the
    other share, RoleBinding grant/revoke, is already covered by `build_role_binding_view_
    invalidation_handler` above under its own `role_binding` category; both categories partition
    the same underlying "does the viewer's own authority need re-evaluation" concern without
    overlap). Tenant-wide scope -- Role itself is not a per-principal fact the way RoleBinding
    is."""

    def handle_authorization_context_event(
        event: _AuthorizationContextEvent,
        context: DomainEventContext,
    ) -> None:
        tenant_id = getattr(event, "tenant_id", None)
        entity_id = getattr(event, "role_id", None) or getattr(event, "policy_name", "")
        channel.notify(
            ViewInvalidationHint(
                scope=TenantScope(tenant_id) if tenant_id else PlatformScope(),
                category=AUTHORIZATION_CONTEXT_CATEGORY,
                scope_code=AUTHORIZATION_CONTEXT_SCOPE_CODE,
                entity_type="role",
                entity_id=entity_id,
            )
        )

    return handle_authorization_context_event


__all__ = [
    "build_authorization_context_view_invalidation_handler",
    "build_role_binding_view_invalidation_handler",
    "AUTHORIZATION_CONTEXT_CATEGORY",
    "AUTHORIZATION_CONTEXT_SCOPE_CODE",
    "ROLE_BINDING_CATEGORY",
    "ROLE_BINDING_ASSIGNMENTS_SCOPE_CODE",
]
