from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from core.platform.common.ids import generate_id


class MaintenanceLifecycleStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    RETIRED = "RETIRED"


class MaintenanceCriticality(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class MaintenancePriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EMERGENCY = "EMERGENCY"


class MaintenanceTriggerMode(str, Enum):
    CALENDAR = "CALENDAR"
    SENSOR = "SENSOR"
    HYBRID = "HYBRID"


@dataclass
class MaintenanceLocation:
    id: str
    organization_id: str
    site_id: str
    location_code: str
    name: str
    description: str = ""
    parent_location_id: str | None = None
    location_type: str = ""
    criticality: MaintenanceCriticality = MaintenanceCriticality.MEDIUM
    status: MaintenanceLifecycleStatus = MaintenanceLifecycleStatus.ACTIVE
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    notes: str = ""
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        site_id: str,
        location_code: str,
        name: str,
        description: str = "",
        parent_location_id: str | None = None,
        location_type: str = "",
        criticality: MaintenanceCriticality = MaintenanceCriticality.MEDIUM,
        status: MaintenanceLifecycleStatus = MaintenanceLifecycleStatus.ACTIVE,
        is_active: bool = True,
        notes: str = "",
    ) -> "MaintenanceLocation":
        now = datetime.now(timezone.utc)
        return MaintenanceLocation(
            id=generate_id(),
            organization_id=organization_id,
            site_id=site_id,
            location_code=location_code,
            name=name,
            description=description,
            parent_location_id=parent_location_id,
            location_type=location_type,
            criticality=criticality,
            status=status,
            is_active=is_active,
            created_at=now,
            updated_at=now,
            notes=notes,
            version=1,
        )


@dataclass
class MaintenanceSystem:
    id: str
    organization_id: str
    site_id: str
    system_code: str
    name: str
    location_id: str | None = None
    description: str = ""
    parent_system_id: str | None = None
    system_type: str = ""
    criticality: MaintenanceCriticality = MaintenanceCriticality.MEDIUM
    status: MaintenanceLifecycleStatus = MaintenanceLifecycleStatus.ACTIVE
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    notes: str = ""
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        site_id: str,
        system_code: str,
        name: str,
        location_id: str | None = None,
        description: str = "",
        parent_system_id: str | None = None,
        system_type: str = "",
        criticality: MaintenanceCriticality = MaintenanceCriticality.MEDIUM,
        status: MaintenanceLifecycleStatus = MaintenanceLifecycleStatus.ACTIVE,
        is_active: bool = True,
        notes: str = "",
    ) -> "MaintenanceSystem":
        now = datetime.now(timezone.utc)
        return MaintenanceSystem(
            id=generate_id(),
            organization_id=organization_id,
            site_id=site_id,
            system_code=system_code,
            name=name,
            location_id=location_id,
            description=description,
            parent_system_id=parent_system_id,
            system_type=system_type,
            criticality=criticality,
            status=status,
            is_active=is_active,
            created_at=now,
            updated_at=now,
            notes=notes,
            version=1,
        )


__all__ = [
    "MaintenanceCriticality",
    "MaintenanceLifecycleStatus",
    "MaintenanceLocation",
    "MaintenancePriority",
    "MaintenanceSystem",
    "MaintenanceTriggerMode",
]
