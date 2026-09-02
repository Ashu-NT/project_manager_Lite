from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ForecastVersionChangeType(str, Enum):
    CREATED = "CREATED"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DELETED = "DELETED"


@dataclass(frozen=True, slots=True, kw_only=True)
class ForecastVersionChanged:
    tenant_id: str
    organization_id: str
    project_id: str
    forecast_id: str
    change_type: ForecastVersionChangeType
    occurred_at: datetime


class ForecastLineChangeType(str, Enum):
    ADDED = "ADDED"
    UPDATED = "UPDATED"
    REMOVED = "REMOVED"


@dataclass(frozen=True, slots=True, kw_only=True)
class ForecastLineChanged:
    """A canonical DomainEvent -- recorded via `uow.record_event(...)`. Forecast lines can
    only be mutated while their owning forecast is mutable (DRAFT/SUBMITTED, never APPROVED
    -- see `ForecastVersionService._require_mutable_forecast`), so a line change never affects
    the project's approved ETC basis; it only invalidates the forecast planning projection."""

    tenant_id: str
    organization_id: str
    project_id: str
    forecast_id: str
    line_id: str
    change_type: ForecastLineChangeType
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ForecastDraftGenerated:
    """A canonical DomainEvent -- recorded via `uow.record_event(...)`. Draft generation is a
    genuinely distinct fact from version/line editing (it atomically snapshots planned cost,
    open commitments, posted actuals, manual estimates, and risk contingencies into one new
    DRAFT forecast plus its `ForecastSourceDecision` audit trail), but its read-model impact is
    identical to `ForecastVersionChanged(CREATED)`: the generated forecast is never
    pre-approved, so only the forecast planning projection goes stale."""

    tenant_id: str
    organization_id: str
    project_id: str
    forecast_id: str
    occurred_at: datetime


__all__ = [
    "ForecastVersionChangeType",
    "ForecastVersionChanged",
    "ForecastLineChangeType",
    "ForecastLineChanged",
    "ForecastDraftGenerated",
]
