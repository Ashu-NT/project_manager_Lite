from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class PartyCreated:
    tenant_id: str
    organization_id: str
    party_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class PartyProfileUpdated:
    tenant_id: str
    organization_id: str
    party_id: str
    occurred_at: datetime


__all__ = ["PartyCreated", "PartyProfileUpdated"]
