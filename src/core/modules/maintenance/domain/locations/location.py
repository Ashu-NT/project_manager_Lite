from __future__ import annotations

from datetime import datetime, timezone

from pydantic import field_validator, model_validator

from src.core.modules.maintenance.domain.enums import (
    MaintenanceCriticality,
    MaintenanceLifecycleStatus,
)
from src.core.modules.maintenance.domain._validation import (
    normalize_criticality,
    normalize_lifecycle_status,
    normalize_maintenance_code,
    normalize_maintenance_name,
    normalize_optional_datetime,
    normalize_optional_identifier,
    normalize_optional_text,
    normalize_positive_int,
    normalize_required_text,
)
from src.core.platform.common.ids import generate_id
from src.core.platform.common.pydantic import validated_dataclass


@validated_dataclass
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
    status: MaintenanceLifecycleStatus | None = None
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    notes: str = ""
    version: int = 1

    @field_validator("id", "organization_id", "site_id", mode="before")
    @classmethod
    def _validate_required_ids(cls, value: object, info) -> str:
        messages = {
            "id": (
                "Maintenance location ID is required.",
                "MAINTENANCE_LOCATION_ID_REQUIRED",
            ),
            "organization_id": (
                "Organization ID is required.",
                "MAINTENANCE_LOCATION_ORGANIZATION_REQUIRED",
            ),
            "site_id": (
                "Site ID is required.",
                "MAINTENANCE_LOCATION_SITE_REQUIRED",
            ),
        }
        message, code = messages[info.field_name]
        return normalize_required_text(value, message=message, code=code)

    @field_validator("location_code", mode="before")
    @classmethod
    def _validate_location_code(cls, value: object) -> str:
        return normalize_maintenance_code(value, label="Location code")

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: object) -> str:
        return normalize_maintenance_name(value, label="Location name")

    @field_validator("parent_location_id", mode="before")
    @classmethod
    def _normalize_parent_location_id(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("description", "location_type", "notes", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("criticality", mode="before")
    @classmethod
    def _validate_criticality(cls, value: object) -> MaintenanceCriticality:
        return normalize_criticality(value)

    @field_validator("status", mode="before")
    @classmethod
    def _normalize_status_input(
        cls,
        value: object,
    ) -> MaintenanceLifecycleStatus | None:
        if value in (None, ""):
            return None
        return normalize_lifecycle_status(value)

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime | None:
        return normalize_optional_datetime(
            value,
            message=f"Maintenance location {info.field_name.replace('_', ' ')} is invalid.",
            code=f"MAINTENANCE_LOCATION_{info.field_name.upper()}_INVALID",
        )

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Maintenance location version must be positive.",
            code="MAINTENANCE_LOCATION_VERSION_INVALID",
        )

    @model_validator(mode="after")
    def _finalize_status(self) -> "MaintenanceLocation":
        object.__setattr__(
            self,
            "status",
            normalize_lifecycle_status(self.status, is_active=self.is_active),
        )
        return self

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
        status: MaintenanceLifecycleStatus | str | None = None,
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


@validated_dataclass
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
    status: MaintenanceLifecycleStatus | None = None
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    notes: str = ""
    version: int = 1

    @field_validator("id", "organization_id", "site_id", mode="before")
    @classmethod
    def _validate_required_ids(cls, value: object, info) -> str:
        messages = {
            "id": (
                "Maintenance system ID is required.",
                "MAINTENANCE_SYSTEM_ID_REQUIRED",
            ),
            "organization_id": (
                "Organization ID is required.",
                "MAINTENANCE_SYSTEM_ORGANIZATION_REQUIRED",
            ),
            "site_id": (
                "Site ID is required.",
                "MAINTENANCE_SYSTEM_SITE_REQUIRED",
            ),
        }
        message, code = messages[info.field_name]
        return normalize_required_text(value, message=message, code=code)

    @field_validator("system_code", mode="before")
    @classmethod
    def _validate_system_code(cls, value: object) -> str:
        return normalize_maintenance_code(value, label="System code")

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: object) -> str:
        return normalize_maintenance_name(value, label="System name")

    @field_validator("location_id", "parent_system_id", mode="before")
    @classmethod
    def _normalize_optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("description", "system_type", "notes", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("criticality", mode="before")
    @classmethod
    def _validate_criticality(cls, value: object) -> MaintenanceCriticality:
        return normalize_criticality(value)

    @field_validator("status", mode="before")
    @classmethod
    def _normalize_status_input(
        cls,
        value: object,
    ) -> MaintenanceLifecycleStatus | None:
        if value in (None, ""):
            return None
        return normalize_lifecycle_status(value)

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime | None:
        return normalize_optional_datetime(
            value,
            message=f"Maintenance system {info.field_name.replace('_', ' ')} is invalid.",
            code=f"MAINTENANCE_SYSTEM_{info.field_name.upper()}_INVALID",
        )

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Maintenance system version must be positive.",
            code="MAINTENANCE_SYSTEM_VERSION_INVALID",
        )

    @model_validator(mode="after")
    def _finalize_status(self) -> "MaintenanceSystem":
        object.__setattr__(
            self,
            "status",
            normalize_lifecycle_status(self.status, is_active=self.is_active),
        )
        return self

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
        status: MaintenanceLifecycleStatus | str | None = None,
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
    "MaintenanceLocation",
    "MaintenanceSystem",
]
