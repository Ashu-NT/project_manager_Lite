"""Maps the five Module Entitlement events (`ModuleLicensed`/`ModuleLicenseRevoked`/
`ModuleEnabled`/`ModuleDisabled`/`ModuleLifecycleTransitioned`) onto one `ViewInvalidationHint`.

All five collapse onto the same stale-read target -- the organization's module entitlement
collection -- because every consumer re-reads that whole collection in one call
(`build_module_entitlements()`), never one module row at a time. One handler, reused across all
five subscriptions in composition, rather than five near-identical copies.

Organization-scoped, never tenant-wide: an organization-specific read must never be invalidated
via a broader `TenantWide`/`AllTenants` filter merely because the eventual re-fetch is tenant-safe.

Transport-independent: no Qt, no QML. Routing is delegated to `ScopeFilter.matches(...)`.
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
