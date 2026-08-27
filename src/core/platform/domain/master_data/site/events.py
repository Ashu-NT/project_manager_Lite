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
class SiteEnabled:
    tenant_id: str
    organization_id: str
    site_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class SiteDisabled:
    tenant_id: str
    organization_id: str
    site_id: str
    occurred_at: datetime


__all__ = ["SiteCreated", "SiteProfileUpdated", "SiteEnabled", "SiteDisabled"]
