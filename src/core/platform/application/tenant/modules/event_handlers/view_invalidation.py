"""ADR-005 Section 12 (P5B-3): the five Module Entitlement business events ->
`ViewInvalidationHint` post-commit reaction.

All five events (`ModuleLicensed`/`ModuleLicenseRevoked`/`ModuleEnabled`/`ModuleDisabled`/
`ModuleLifecycleTransitioned`) collapse onto the SAME single stale-read target -- the
organization's module entitlement collection -- because every real consumer re-reads that whole
collection in one call (`build_module_entitlements()`), never one module row at a time. One
mapping handler, reused across all five `post_commit_bus.subscribe(...)` registrations in
composition (`platform_registry.py`), rather than five near-identical copies.

Organization-scoped, never tenant-wide or all-tenants: each event already carries its own
`organization_id`, and the Organization P6A hardening review established that an
organization-specific read must never be invalidated via a broader `TenantWide`/`AllTenants`
filter merely because the eventual re-fetch is itself tenant-safe.

Transport-independent: no Qt, no QML. Routing is delegated entirely to `ScopeFilter.matches(...)`
via the P2 `ViewInvalidationChannel` -- this module never reimplements tenant/organization
matching itself. The Qt adapter consumes `ViewInvalidationHint`, never these events directly.
"""

from __future__ import annotations

from src.core.platform.domain.tenant.modules.events import (
    ModuleDisabled,
    ModuleEnabled,
    ModuleLicenseRevoked,
    ModuleLicensed,
    ModuleLifecycleTransitioned,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    OrganizationScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

MODULE_ENTITLEMENT_CATEGORY = "module_entitlement"
MODULE_ENTITLEMENTS_SCOPE_CODE = "module_entitlements"

_ModuleEntitlementEvent = (
    ModuleLicensed | ModuleLicenseRevoked | ModuleEnabled | ModuleDisabled | ModuleLifecycleTransitioned
)


def build_module_entitlement_view_invalidation_handler(channel: ViewInvalidationChannel):
    """Returns one `PostCommitEventHandler` bound to `channel`, reused for explicit composition-root
    registration against all five Module Entitlement events
    (`post_commit_bus.subscribe(ModuleLicensed, handler)`, ..., `subscribe(ModuleLifecycleTransitioned, handler)`)."""

    def handle_module_entitlement_event(event: _ModuleEntitlementEvent, context: DomainEventContext) -> None:
        channel.notify(
            ViewInvalidationHint(
                scope=OrganizationScope(event.tenant_id, event.organization_id),
                category=MODULE_ENTITLEMENT_CATEGORY,
                scope_code=MODULE_ENTITLEMENTS_SCOPE_CODE,
                entity_type="module_entitlement",
                entity_id=None,
            )
        )

    return handle_module_entitlement_event


__all__ = [
    "build_module_entitlement_view_invalidation_handler",
    "MODULE_ENTITLEMENT_CATEGORY",
    "MODULE_ENTITLEMENTS_SCOPE_CODE",
]
