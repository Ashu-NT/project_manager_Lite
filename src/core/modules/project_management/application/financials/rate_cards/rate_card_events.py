from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class RateCardCreated:
    tenant_id: str
    organization_id: str
    rate_card_id: str
    project_id: str | None
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class RateCardDeactivated:
    tenant_id: str
    organization_id: str
    rate_card_id: str
    project_id: str | None
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class RateCardLineAdded:
    tenant_id: str
    organization_id: str
    rate_card_id: str
    rate_line_id: str
    project_id: str | None
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class RateCardLineUpdated:
    tenant_id: str
    organization_id: str
    rate_card_id: str
    rate_line_id: str
    project_id: str | None
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class RateCardLineDeactivated:
    tenant_id: str
    organization_id: str
    rate_card_id: str
    rate_line_id: str
    project_id: str | None
    occurred_at: datetime


__all__ = [
    "RateCardCreated",
    "RateCardDeactivated",
    "RateCardLineAdded",
    "RateCardLineUpdated",
    "RateCardLineDeactivated",
]
