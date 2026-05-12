from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from src.core.modules.maintenance.domain.enums import (
    MaintenancePriority,
    MaintenanceWorkRequestSourceType,
    MaintenanceWorkRequestStatus,
)
from src.core.platform.common.ids import generate_id


@dataclass
class MaintenanceWorkRequest:
    id: str
    organization_id: str
    site_id: str
    work_request_code: str
    source_type: MaintenanceWorkRequestSourceType
    request_type: str
    source_id: str | None = None
    source_plan_task_ids: tuple[str, ...] = ()
    asset_id: str | None = None
    component_id: str | None = None
    system_id: str | None = None
    location_id: str | None = None
    title: str = ""
    description: str = ""
    priority: MaintenancePriority = MaintenancePriority.MEDIUM
    status: MaintenanceWorkRequestStatus = MaintenanceWorkRequestStatus.NEW
    requested_at: datetime | None = None
    requested_by_user_id: str | None = None
    requested_by_name_snapshot: str = ""
    triaged_at: datetime | None = None
    triaged_by_user_id: str | None = None
    failure_symptom_code: str = ""
    safety_risk_level: str = ""
    production_impact_level: str = ""
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        site_id: str,
        work_request_code: str,
        source_type: MaintenanceWorkRequestSourceType,
        request_type: str,
        source_id: str | None = None,
        source_plan_task_ids: tuple[str, ...] = (),
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        location_id: str | None = None,
        title: str = "",
        description: str = "",
        priority: MaintenancePriority = MaintenancePriority.MEDIUM,
        requested_by_user_id: str | None = None,
        requested_by_name_snapshot: str = "",
        failure_symptom_code: str = "",
        safety_risk_level: str = "",
        production_impact_level: str = "",
        notes: str = "",
    ) -> "MaintenanceWorkRequest":
        now = datetime.now(timezone.utc)
        return MaintenanceWorkRequest(
            id=generate_id(),
            organization_id=organization_id,
            site_id=site_id,
            work_request_code=work_request_code,
            source_type=source_type,
            source_id=source_id,
            source_plan_task_ids=tuple(source_plan_task_ids),
            request_type=request_type,
            asset_id=asset_id,
            component_id=component_id,
            system_id=system_id,
            location_id=location_id,
            title=title,
            description=description,
            priority=priority,
            status=MaintenanceWorkRequestStatus.NEW,
            requested_at=now,
            requested_by_user_id=requested_by_user_id,
            requested_by_name_snapshot=requested_by_name_snapshot,
            failure_symptom_code=failure_symptom_code,
            safety_risk_level=safety_risk_level,
            production_impact_level=production_impact_level,
            notes=notes,
            created_at=now,
            updated_at=now,
            version=1,
        )


__all__ = ["MaintenanceWorkRequest"]
