"""Module Entitlement's own business event vocabulary.

Application-authored via `uow.record_event(...)` from `ModuleCatalogMutationMixin`
(platform_p5_event_discovery.md Section 8, mirroring `OrganizationCreated`'s own precedent):
`ModuleEntitlement` is a plain projection with no transition methods (P5B-SEM's own finding), so
these are application-recorded, not aggregate-recorded.

Pure business vocabulary only -- no ViewInvalidation import, no legacy `domain_events` Signal
import, no dispatch/execution metadata (`correlation_id`/`causation_id`/`command_id` live on
`DomainEventContext`, never duplicated here).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ModuleLicensed:
    tenant_id: str
    organization_id: str
    module_code: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ModuleLicenseRevoked:
    tenant_id: str
    organization_id: str
    module_code: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ModuleEnabled:
    tenant_id: str
    organization_id: str
    module_code: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ModuleDisabled:
    tenant_id: str
    organization_id: str
    module_code: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ModuleLifecycleTransitioned:
    tenant_id: str
    organization_id: str
    module_code: str
    previous_lifecycle_status: str
    lifecycle_status: str
    occurred_at: datetime


__all__ = [
    "ModuleLicensed",
    "ModuleLicenseRevoked",
    "ModuleEnabled",
    "ModuleDisabled",
    "ModuleLifecycleTransitioned",
]
