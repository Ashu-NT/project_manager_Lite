from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class TimesheetPeriodStatusChangeType(str, Enum):
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    LOCKED = "LOCKED"
    UNLOCKED = "UNLOCKED"
    REOPENED_FOR_CORRECTION = "REOPENED_FOR_CORRECTION"


@dataclass(frozen=True, slots=True, kw_only=True)
class TimesheetPeriodStatusChanged:
    tenant_id: str
    organization_id: str
    period_id: str
    resource_id: str
    change_type: TimesheetPeriodStatusChangeType
    project_ids: tuple[str, ...]
    occurred_at: datetime


__all__ = ["TimesheetPeriodStatusChangeType", "TimesheetPeriodStatusChanged"]
