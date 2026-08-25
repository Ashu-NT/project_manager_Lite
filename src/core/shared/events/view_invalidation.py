"""ADR-005 §12 (View Invalidation): a transport-independent hint that an authoritative
read/view is stale and should be re-read.

Never a business fact -- never routed through the same contract as a `DomainEvent`. Contains
only targeting fields: `scope`, `category`, `scope_code`, `entity_type`, `entity_id`.

Scope is a closed, three-kind `EventScope` union (`PlatformScope`/`TenantScope`/
`OrganizationScope`), replacing an earlier, rejected design that used plain
`tenant_id`/`organization_id: str | None` fields directly on the hint plus five separately-named
channel subscription methods. Under the flat shape, `organization_id=None` had to carry the
entire weight of meaning "intentionally tenant-wide" by convention alone; under the typed union,
a `TenantScope` has no `organization_id` field to be ambiguous about -- the invariant is a fact
about the type system, not a fact developers must remember (ADR-005 §12).

`DomainEvent` deliberately does NOT adopt `EventScope` -- see ADR-005 §3: a business-fact
dataclass's `tenant_id`/`organization_id` are plain vocabulary read alongside its other identifier
fields, whereas `ViewInvalidationHint` is transport/filtering infrastructure, precisely where a
subscriber needs to reason about *breadth* of interest -- a concept `DomainEvent` never needs.

Subscription is one `subscribe(filter, handler)` method, parameterized by a small, closed,
independently-extensible `ScopeFilter` hierarchy -- not five separately-named channel methods.
`ScopeFilter` is a distinct concept from `EventScope`: "breadth of interest" is a property of
what a subscriber wants, never a kind of scope a fact itself can have.

No concrete channel implementation here -- P2 (`src/infra/events/in_process_view_invalidation_channel.py`)
and P6 (the Qt adapter) build on this contract; this file only defines it.
"""

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
