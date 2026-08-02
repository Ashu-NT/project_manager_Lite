from __future__ import annotations

from datetime import datetime, timezone

from pydantic import field_validator, model_validator

from src.core.modules.maintenance.domain._validation import (
    normalize_identifier_tuple,
    normalize_maintenance_code,
    normalize_maintenance_name,
    normalize_optional_datetime,
    normalize_optional_identifier,
    normalize_optional_text,
    normalize_optional_upper_text,
    normalize_positive_int,
    normalize_priority,
    normalize_required_text,
    normalize_work_request_source_type,
    normalize_work_request_status,
)
from src.core.modules.maintenance.domain.enums import (
    MaintenancePriority,
    MaintenanceWorkRequestSourceType,
    MaintenanceWorkRequestStatus,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.ids import generate_id
from src.core.platform.common.pydantic import validated_dataclass


@validated_dataclass
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

    @field_validator("id", "organization_id", "site_id", mode="before")
    @classmethod
    def _validate_required_ids(cls, value: object, info) -> str:
        messages = {
            "id": (
                "Maintenance work request ID is required.",
                "MAINTENANCE_WORK_REQUEST_ID_REQUIRED",
            ),
            "organization_id": (
                "Organization ID is required.",
                "MAINTENANCE_WORK_REQUEST_ORGANIZATION_REQUIRED",
            ),
            "site_id": (
                "Site ID is required.",
                "MAINTENANCE_WORK_REQUEST_SITE_REQUIRED",
            ),
        }
        message, code = messages[info.field_name]
        return normalize_required_text(value, message=message, code=code)

    @field_validator("work_request_code", mode="before")
    @classmethod
    def _validate_work_request_code(cls, value: object) -> str:
        return normalize_maintenance_code(value, label="Work request code")

    @field_validator("source_type", mode="before")
    @classmethod
    def _validate_source_type(cls, value: object) -> MaintenanceWorkRequestSourceType:
        return normalize_work_request_source_type(value)

    @field_validator("request_type", mode="before")
    @classmethod
    def _validate_request_type(cls, value: object) -> str:
        return normalize_maintenance_name(value, label="Request type").upper()

    @field_validator(
        "source_id",
        "asset_id",
        "component_id",
        "system_id",
        "location_id",
        "requested_by_user_id",
        "triaged_by_user_id",
        mode="before",
    )
    @classmethod
    def _normalize_optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("source_plan_task_ids", mode="before")
    @classmethod
    def _normalize_source_plan_task_ids(cls, value: object) -> tuple[str, ...]:
        return normalize_identifier_tuple(value)

    @field_validator(
        "title",
        "description",
        "requested_by_name_snapshot",
        "notes",
        mode="before",
    )
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator(
        "failure_symptom_code",
        "safety_risk_level",
        "production_impact_level",
        mode="before",
    )
    @classmethod
    def _normalize_upper_text_fields(cls, value: object) -> str:
        return normalize_optional_upper_text(value)

    @field_validator("priority", mode="before")
    @classmethod
    def _validate_priority(cls, value: object) -> MaintenancePriority:
        return normalize_priority(value)

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, value: object) -> MaintenanceWorkRequestStatus:
        return normalize_work_request_status(value)

    @field_validator(
        "requested_at",
        "triaged_at",
        "created_at",
        "updated_at",
        mode="before",
    )
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime | None:
        return normalize_optional_datetime(
            value,
            message=f"Maintenance work request {info.field_name.replace('_', ' ')} is invalid.",
            code=f"MAINTENANCE_WORK_REQUEST_{info.field_name.upper()}_INVALID",
        )

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Maintenance work request version must be positive.",
            code="MAINTENANCE_WORK_REQUEST_VERSION_INVALID",
        )

    @model_validator(mode="after")
    def _validate_ranges(self) -> "MaintenanceWorkRequest":
        if (
            self.triaged_at is not None
            and self.requested_at is not None
            and self.triaged_at < self.requested_at
        ):
            raise ValidationError(
                "Triaged timestamp cannot be earlier than requested timestamp.",
                code="MAINTENANCE_WORK_REQUEST_TRIAGE_RANGE_INVALID",
            )
        if (
            self.updated_at is not None
            and self.created_at is not None
            and self.updated_at < self.created_at
        ):
            raise ValidationError(
                "Updated timestamp cannot be earlier than created timestamp.",
                code="MAINTENANCE_WORK_REQUEST_UPDATED_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        *,
        organization_id: str,
        site_id: str,
        work_request_code: str,
        source_type: MaintenanceWorkRequestSourceType | str | None,
        request_type: str,
        source_id: str | None = None,
        source_plan_task_ids: tuple[str, ...] = (),
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        location_id: str | None = None,
        title: str = "",
        description: str = "",
        priority: MaintenancePriority | str | None = None,
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
