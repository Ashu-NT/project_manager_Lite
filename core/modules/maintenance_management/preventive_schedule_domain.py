from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from core.platform.common.ids import generate_id


class MaintenanceSchedulePolicy(str, Enum):
    FIXED = "FIXED"
    FLOATING = "FLOATING"


class MaintenanceGenerationLeadUnit(str, Enum):
    DAYS = "DAYS"
    WEEKS = "WEEKS"
    MONTHS = "MONTHS"


class MaintenancePreventiveInstanceStatus(str, Enum):
    PLANNED = "PLANNED"
    GENERATED = "GENERATED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


@dataclass
class MaintenancePreventivePlanInstance:
    id: str
    organization_id: str
    plan_id: str
    due_at: datetime
    due_counter: Decimal | None = None
    status: MaintenancePreventiveInstanceStatus = MaintenancePreventiveInstanceStatus.PLANNED
    generated_at: datetime | None = None
    generated_work_request_id: str | None = None
    generated_work_order_id: str | None = None
    completed_at: datetime | None = None
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        plan_id: str,
        due_at: datetime,
        due_counter: Decimal | None = None,
        status: MaintenancePreventiveInstanceStatus = MaintenancePreventiveInstanceStatus.PLANNED,
        generated_at: datetime | None = None,
        generated_work_request_id: str | None = None,
        generated_work_order_id: str | None = None,
        completed_at: datetime | None = None,
        notes: str = "",
    ) -> "MaintenancePreventivePlanInstance":
        now = datetime.now(timezone.utc)
        return MaintenancePreventivePlanInstance(
            id=generate_id(),
            organization_id=organization_id,
            plan_id=plan_id,
            due_at=due_at,
            due_counter=due_counter,
            status=status,
            generated_at=generated_at,
            generated_work_request_id=generated_work_request_id,
            generated_work_order_id=generated_work_order_id,
            completed_at=completed_at,
            notes=notes,
            created_at=now,
            updated_at=now,
            version=1,
        )


__all__ = [
    "MaintenanceGenerationLeadUnit",
    "MaintenancePreventiveInstanceStatus",
    "MaintenancePreventivePlanInstance",
    "MaintenanceSchedulePolicy",
]
