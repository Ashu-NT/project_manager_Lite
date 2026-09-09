"""Organization's business event vocabulary. Application-authored via `uow.record_event(...)`
from `OrganizationService` -- Organization has no state-transition methods of its own. Pure
business vocabulary only: no ViewInvalidation import, no dispatch/execution metadata
(`correlation_id`/`causation_id`/`command_id` live on `DomainEventContext`, never duplicated here).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class OrganizationCreated:
    tenant_id: str
    organization_id: str
    name: str
    code: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class OrganizationProfileUpdated:
    """A committed change to one or more of an Organization's profile fields (code, display
    name, timezone, base currency) -- never emitted for a no-op update. Identifiers only: no
    handler needs the changed values, only that the tenant's organization collection is stale."""

    tenant_id: str
    organization_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class OrganizationEnabled:
    """`Organization.is_enabled` committed False -> True; never emitted for an already-enabled
    organization. Not a session-selection event -- see `TenantContextService.
    set_active_organization`, which is untouched by this vocabulary."""

    tenant_id: str
    organization_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class OrganizationDisabled:
    """`Organization.is_enabled` committed True -> False; never emitted for an already-disabled
    organization. See `OrganizationEnabled`'s own note on session selection."""

    tenant_id: str
    organization_id: str
    occurred_at: datetime


__all__ = [
    "OrganizationCreated",
    "OrganizationDisabled",
    "OrganizationEnabled",
    "OrganizationProfileUpdated",
]
