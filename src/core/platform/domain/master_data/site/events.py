from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class SiteCreated:
    tenant_id: str
    organization_id: str
    site_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class SiteProfileUpdated:
    tenant_id: str
    organization_id: str
    site_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class SiteActivated:
    tenant_id: str
    organization_id: str
    site_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class SiteDeactivated:
    tenant_id: str
    organization_id: str
    site_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class SiteArchived:
    tenant_id: str
    organization_id: str
    site_id: str
    occurred_at: datetime


__all__ = [
    "SiteActivated",
    "SiteArchived",
    "SiteCreated",
    "SiteDeactivated",
    "SiteProfileUpdated",
]
