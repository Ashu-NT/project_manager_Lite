from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypeVar

from src.core.shared.events.subscription import Subscription


class EventScope(Protocol):
    """A closed union of exactly three kinds -- sealed by convention (only PlatformScope,
    TenantScope, and OrganizationScope implement it; do not add a fourth without revisiting
    ADR-005 §12)."""


@dataclass(frozen=True, slots=True)
class PlatformScope(EventScope):
    """No tenant at all. Genuinely installation-wide facts only."""


@dataclass(frozen=True, slots=True)
class TenantScope(EventScope):
    """Tenant-wide -- NOT organization-scoped. There is no organization_id field on this
    type at all; a fact that belongs to one organization is never represented this way."""

    tenant_id: str


@dataclass(frozen=True, slots=True)
class OrganizationScope(EventScope):
    """Exactly one organization within one tenant. organization_id is a required
    constructor argument -- there is no way to construct this type without one."""

    tenant_id: str
    organization_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ViewInvalidationHint:
    scope: EventScope  # PlatformScope | TenantScope | OrganizationScope
    category: str
    scope_code: str
    entity_type: str
    entity_id: str | None = None
    module_code: str | None = None


H = TypeVar("H", bound=ViewInvalidationHint)


class ViewInvalidationHandler(Protocol[H]):
    def __call__(self, hint: H) -> None: ...


class ScopeFilter(Protocol):
    def matches(self, scope: EventScope) -> bool: ...


@dataclass(frozen=True, slots=True)
class ExactOrganization(ScopeFilter):
    """This organization's views only. A hint for a different organization in the same
    tenant, or a tenant-wide hint, is never delivered here."""

    tenant_id: str
    organization_id: str

    def matches(self, scope: EventScope) -> bool:
        return (
            isinstance(scope, OrganizationScope)
            and scope.tenant_id == self.tenant_id
            and scope.organization_id == self.organization_id
        )


@dataclass(frozen=True, slots=True)
class TenantWide(ScopeFilter):
    """Only genuinely tenant-wide facts for this tenant. An organization-scoped hint, even
    for an organization in this same tenant, is never delivered here."""

    tenant_id: str

    def matches(self, scope: EventScope) -> bool:
        return isinstance(scope, TenantScope) and scope.tenant_id == self.tenant_id


@dataclass(frozen=True, slots=True)
class AnyOrganizationInTenant(ScopeFilter):
    """Deliberate breadth: every hint for this tenant, tenant-wide or any organization's.
    For genuine tenant-admin/organization-selector screens -- a searchable, auditable
    opt-in, never the default."""

    tenant_id: str

    def matches(self, scope: EventScope) -> bool:
        return isinstance(scope, (TenantScope, OrganizationScope)) and scope.tenant_id == self.tenant_id


@dataclass(frozen=True, slots=True)
class AllTenants(ScopeFilter):
    """Every tenant's hints. Rare, auditable, platform-admin-only. Not to be conflated with
    AnyOrganizationInTenant, which is still scoped to one tenant."""

    def matches(self, scope: EventScope) -> bool:
        return isinstance(scope, (TenantScope, OrganizationScope))


@dataclass(frozen=True, slots=True)
class PlatformWide(ScopeFilter):
    """Only genuinely platform-wide facts -- never a tenant-scoped hint of any kind."""

    def matches(self, scope: EventScope) -> bool:
        return isinstance(scope, PlatformScope)


class ViewInvalidationChannel(Protocol):
    def notify(self, hint: ViewInvalidationHint) -> None: ...

    def subscribe(
        self,
        filter: ScopeFilter,
        handler: ViewInvalidationHandler[ViewInvalidationHint],
    ) -> Subscription: ...


__all__ = [
    "EventScope",
    "PlatformScope",
    "TenantScope",
    "OrganizationScope",
    "ViewInvalidationHint",
    "ViewInvalidationHandler",
    "ScopeFilter",
    "ExactOrganization",
    "TenantWide",
    "AnyOrganizationInTenant",
    "AllTenants",
    "PlatformWide",
    "ViewInvalidationChannel",
]
