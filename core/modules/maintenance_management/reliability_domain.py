from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from src.core.platform.common.ids import generate_id


class MaintenanceFailureCodeType(str, Enum):
    SYMPTOM = "SYMPTOM"
    CAUSE = "CAUSE"
    REMEDY = "REMEDY"


@dataclass
class MaintenanceDowntimeEvent:
    id: str
    organization_id: str
    asset_id: str | None = None
    system_id: str | None = None
    work_order_id: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_minutes: int | None = None
    downtime_type: str = ""
    reason_code: str = ""
    impact_notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        started_at: datetime,
        downtime_type: str,
        asset_id: str | None = None,
        system_id: str | None = None,
        work_order_id: str | None = None,
        ended_at: datetime | None = None,
        duration_minutes: int | None = None,
        reason_code: str = "",
        impact_notes: str = "",
    ) -> "MaintenanceDowntimeEvent":
        now = datetime.now(timezone.utc)
        return MaintenanceDowntimeEvent(
            id=generate_id(),
            organization_id=organization_id,
            asset_id=asset_id,
            system_id=system_id,
            work_order_id=work_order_id,
            started_at=started_at,
            ended_at=ended_at,
            duration_minutes=duration_minutes,
            downtime_type=downtime_type,
            reason_code=reason_code,
            impact_notes=impact_notes,
            created_at=now,
            updated_at=now,
            version=1,
        )


@dataclass
class MaintenanceFailureCode:
    id: str
    organization_id: str
    failure_code: str
    name: str
    description: str = ""
    code_type: MaintenanceFailureCodeType = MaintenanceFailureCodeType.SYMPTOM
    parent_code_id: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        failure_code: str,
        name: str,
        description: str = "",
        code_type: MaintenanceFailureCodeType = MaintenanceFailureCodeType.SYMPTOM,
        parent_code_id: str | None = None,
        is_active: bool = True,
    ) -> "MaintenanceFailureCode":
        now = datetime.now(timezone.utc)
        return MaintenanceFailureCode(
            id=generate_id(),
            organization_id=organization_id,
            failure_code=failure_code,
            name=name,
            description=description,
            code_type=code_type,
            parent_code_id=parent_code_id,
            is_active=is_active,
            created_at=now,
            updated_at=now,
            version=1,
        )


__all__ = [
    "MaintenanceDowntimeEvent",
    "MaintenanceFailureCode",
    "MaintenanceFailureCodeType",
]
