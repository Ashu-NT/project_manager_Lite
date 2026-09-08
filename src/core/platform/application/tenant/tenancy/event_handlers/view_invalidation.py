
from __future__ import annotations

from src.core.platform.domain.security.auth.events import TenantMembershipProvisioned
from src.core.platform.domain.tenant.tenancy.events import (
    TenantMembershipActivated,
    TenantMembershipReactivated,
    TenantMembershipRemoved,
    TenantMembershipSuspended,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    TenantScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

TENANT_MEMBERSHIP_CATEGORY = "tenant_membership"
TENANT_MEMBERSHIPS_SCOPE_CODE = "tenant_memberships"

_TenantMembershipEvent = (
    TenantMembershipActivated
    | TenantMembershipSuspended
    | TenantMembershipReactivated
    | TenantMembershipRemoved
    | TenantMembershipProvisioned
)


def build_tenant_membership_view_invalidation_handler(channel: ViewInvalidationChannel):
    """Returns one `PostCommitEventHandler` bound to `channel`, reused for explicit
    composition-root registration against all five membership events (`Activated`, `Suspended`,
    `Reactivated`, `Removed`, `Provisioned`). `Provisioned` is a genuinely different creation path
    (system/admin-direct, not invite->accept) but has an identical membership_id/tenant_id-shaped
    view-invalidation need, so it reuses this same target rather than a parallel one."""

    def handle_tenant_membership_event(
        event: _TenantMembershipEvent, context: DomainEventContext
    ) -> None:
        channel.notify(
            ViewInvalidationHint(
                scope=TenantScope(event.tenant_id),
                category=TENANT_MEMBERSHIP_CATEGORY,
                scope_code=TENANT_MEMBERSHIPS_SCOPE_CODE,
                entity_type="tenant_membership",
                entity_id=event.membership_id,
            )
        )

    return handle_tenant_membership_event


__all__ = [
    "TENANT_MEMBERSHIPS_SCOPE_CODE",
    "TENANT_MEMBERSHIP_CATEGORY",
    "build_tenant_membership_view_invalidation_handler",
]
