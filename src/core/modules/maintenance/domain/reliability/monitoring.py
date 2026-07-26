from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from pydantic import field_validator, model_validator

from src.core.modules.maintenance.domain._validation import (
    normalize_failure_code_type,
    normalize_maintenance_code,
    normalize_maintenance_name,
    normalize_optional_datetime,
    normalize_optional_decimal_value,
    normalize_optional_identifier,
    normalize_optional_non_negative_int,
    normalize_optional_text,
    normalize_optional_upper_text,
    normalize_positive_int,
    normalize_required_text,
    normalize_sensor_exception_status,
    normalize_sensor_exception_type,
    normalize_sensor_quality_state,
)
from src.core.modules.maintenance.domain.enums import (
    MaintenanceFailureCodeType,
    MaintenanceSensorExceptionStatus,
    MaintenanceSensorExceptionType,
    MaintenanceSensorQualityState,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.ids import generate_id
from src.core.platform.common.pydantic import validated_dataclass


@validated_dataclass
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

    @field_validator("id", "organization_id", mode="before")
    @classmethod
    def _validate_required_ids(cls, value: object, info) -> str:
        messages = {
            "id": (
                "Maintenance downtime event ID is required.",
                "MAINTENANCE_DOWNTIME_EVENT_ID_REQUIRED",
            ),
            "organization_id": (
                "Organization ID is required.",
                "MAINTENANCE_DOWNTIME_EVENT_ORGANIZATION_REQUIRED",
            ),
        }
        message, code = messages[info.field_name]
        return normalize_required_text(value, message=message, code=code)

    @field_validator("asset_id", "system_id", "work_order_id", mode="before")
    @classmethod
    def _normalize_optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("started_at", mode="before")
    @classmethod
    def _validate_started_at(cls, value: object) -> datetime:
        resolved = normalize_optional_datetime(
            value,
            message="Maintenance downtime event start is invalid.",
            code="MAINTENANCE_DOWNTIME_EVENT_STARTED_AT_INVALID",
        )
        if resolved is None:
            raise ValidationError(
                "Downtime start is required.",
                code="MAINTENANCE_DOWNTIME_START_REQUIRED",
            )
        return resolved

    @field_validator("ended_at", "created_at", "updated_at", mode="before")
    @classmethod
    def _validate_optional_datetimes(cls, value: object, info) -> datetime | None:
        return normalize_optional_datetime(
            value,
            message=f"Maintenance downtime event {info.field_name.replace('_', ' ')} is invalid.",
            code=f"MAINTENANCE_DOWNTIME_EVENT_{info.field_name.upper()}_INVALID",
        )

    @field_validator("duration_minutes", mode="before")
    @classmethod
    def _validate_duration_minutes(cls, value: object) -> int | None:
        return normalize_optional_non_negative_int(value, label="Downtime duration minutes")

    @field_validator("downtime_type", mode="before")
    @classmethod
    def _validate_downtime_type(cls, value: object) -> str:
        return normalize_maintenance_name(value, label="Downtime type").upper()

    @field_validator("reason_code", mode="before")
    @classmethod
    def _normalize_reason_code(cls, value: object) -> str:
        return normalize_optional_upper_text(value)

    @field_validator("impact_notes", mode="before")
    @classmethod
    def _normalize_impact_notes(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Maintenance downtime event version must be positive.",
            code="MAINTENANCE_DOWNTIME_EVENT_VERSION_INVALID",
        )

    @model_validator(mode="after")
    def _validate_ranges(self) -> "MaintenanceDowntimeEvent":
        if self.ended_at is not None and self.ended_at < self.started_at:
            raise ValidationError(
                "Downtime end cannot be earlier than downtime start.",
                code="MAINTENANCE_DOWNTIME_RANGE_INVALID",
            )
        if (
            self.updated_at is not None
            and self.created_at is not None
            and self.updated_at < self.created_at
        ):
            raise ValidationError(
                "Updated timestamp cannot be earlier than created timestamp.",
                code="MAINTENANCE_DOWNTIME_EVENT_UPDATED_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        *,
        organization_id: str,
        started_at: datetime | str,
        downtime_type: str,
        asset_id: str | None = None,
        system_id: str | None = None,
        work_order_id: str | None = None,
        ended_at: datetime | str | None = None,
        duration_minutes: int | str | None = None,
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


@validated_dataclass
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

    @field_validator("id", "organization_id", mode="before")
    @classmethod
    def _validate_required_ids(cls, value: object, info) -> str:
        messages = {
            "id": (
                "Maintenance failure code ID is required.",
                "MAINTENANCE_FAILURE_CODE_ID_REQUIRED",
            ),
            "organization_id": (
                "Organization ID is required.",
                "MAINTENANCE_FAILURE_CODE_ORGANIZATION_REQUIRED",
            ),
        }
        message, code = messages[info.field_name]
        return normalize_required_text(value, message=message, code=code)

    @field_validator("failure_code", mode="before")
    @classmethod
    def _validate_failure_code(cls, value: object) -> str:
        return normalize_maintenance_code(value, label="Failure code")

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: object) -> str:
        return normalize_maintenance_name(value, label="Failure code name")

    @field_validator("description", mode="before")
    @classmethod
    def _normalize_description(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("code_type", mode="before")
    @classmethod
    def _validate_code_type(cls, value: object) -> MaintenanceFailureCodeType:
        return normalize_failure_code_type(value)

    @field_validator("parent_code_id", mode="before")
    @classmethod
    def _normalize_parent_code_id(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime | None:
        return normalize_optional_datetime(
            value,
            message=f"Maintenance failure code {info.field_name.replace('_', ' ')} is invalid.",
            code=f"MAINTENANCE_FAILURE_CODE_{info.field_name.upper()}_INVALID",
        )

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Maintenance failure code version must be positive.",
            code="MAINTENANCE_FAILURE_CODE_VERSION_INVALID",
        )

    @model_validator(mode="after")
    def _validate_ranges(self) -> "MaintenanceFailureCode":
        if (
            self.updated_at is not None
            and self.created_at is not None
            and self.updated_at < self.created_at
        ):
            raise ValidationError(
                "Updated timestamp cannot be earlier than created timestamp.",
                code="MAINTENANCE_FAILURE_CODE_UPDATED_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        *,
        organization_id: str,
        failure_code: str,
        name: str,
        description: str = "",
        code_type: MaintenanceFailureCodeType | str | None = MaintenanceFailureCodeType.SYMPTOM,
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


@validated_dataclass
class MaintenanceSensor:
    id: str
    organization_id: str
    site_id: str
    sensor_code: str
    sensor_name: str
    sensor_tag: str = ""
    sensor_type: str = ""
    asset_id: str | None = None
    component_id: str | None = None
    system_id: str | None = None
    source_type: str = ""
    source_name: str = ""
    source_key: str = ""
    unit: str = ""
    current_value: Decimal | None = None
    last_read_at: datetime | None = None
    last_quality_state: MaintenanceSensorQualityState = MaintenanceSensorQualityState.VALID
    is_active: bool = True
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @field_validator("id", "organization_id", "site_id", mode="before")
    @classmethod
    def _validate_required_ids(cls, value: object, info) -> str:
        messages = {
            "id": ("Maintenance sensor ID is required.", "MAINTENANCE_SENSOR_ID_REQUIRED"),
            "organization_id": (
                "Organization ID is required.",
                "MAINTENANCE_SENSOR_ORGANIZATION_REQUIRED",
            ),
            "site_id": ("Site ID is required.", "MAINTENANCE_SENSOR_SITE_REQUIRED"),
        }
        message, code = messages[info.field_name]
        return normalize_required_text(value, message=message, code=code)

    @field_validator("sensor_code", mode="before")
    @classmethod
    def _validate_sensor_code(cls, value: object) -> str:
        return normalize_maintenance_code(value, label="Sensor code")

    @field_validator("sensor_name", mode="before")
    @classmethod
    def _validate_sensor_name(cls, value: object) -> str:
        return normalize_maintenance_name(value, label="Sensor name")

    @field_validator("asset_id", "component_id", "system_id", mode="before")
    @classmethod
    def _normalize_optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("sensor_tag", "source_name", "source_key", "notes", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("sensor_type", "source_type", "unit", mode="before")
    @classmethod
    def _normalize_upper_text_fields(cls, value: object) -> str:
        return normalize_optional_upper_text(value)

    @field_validator("current_value", mode="before")
    @classmethod
    def _validate_current_value(cls, value: object) -> Decimal | None:
        return normalize_optional_decimal_value(value, label="Current value")

    @field_validator("last_read_at", "created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime | None:
        return normalize_optional_datetime(
            value,
            message=f"Maintenance sensor {info.field_name.replace('_', ' ')} is invalid.",
            code=f"MAINTENANCE_SENSOR_{info.field_name.upper()}_INVALID",
        )

    @field_validator("last_quality_state", mode="before")
    @classmethod
    def _validate_quality_state(cls, value: object) -> MaintenanceSensorQualityState:
        return normalize_sensor_quality_state(value)

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Maintenance sensor version must be positive.",
            code="MAINTENANCE_SENSOR_VERSION_INVALID",
        )

    @model_validator(mode="after")
    def _validate_ranges(self) -> "MaintenanceSensor":
        if (
            self.updated_at is not None
            and self.created_at is not None
            and self.updated_at < self.created_at
        ):
            raise ValidationError(
                "Updated timestamp cannot be earlier than created timestamp.",
                code="MAINTENANCE_SENSOR_UPDATED_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        *,
        organization_id: str,
        site_id: str,
        sensor_code: str,
        sensor_name: str,
        sensor_tag: str = "",
        sensor_type: str = "",
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        source_type: str = "",
        source_name: str = "",
        source_key: str = "",
        unit: str = "",
        current_value: Decimal | int | float | str | None = None,
        last_read_at: datetime | str | None = None,
        last_quality_state: MaintenanceSensorQualityState | str | None = MaintenanceSensorQualityState.VALID,
        is_active: bool = True,
        notes: str = "",
    ) -> "MaintenanceSensor":
        now = datetime.now(timezone.utc)
        return MaintenanceSensor(
            id=generate_id(),
            organization_id=organization_id,
            site_id=site_id,
            sensor_code=sensor_code,
            sensor_name=sensor_name,
            sensor_tag=sensor_tag,
            sensor_type=sensor_type,
            asset_id=asset_id,
            component_id=component_id,
            system_id=system_id,
            source_type=source_type,
            source_name=source_name,
            source_key=source_key,
            unit=unit,
            current_value=current_value,
            last_read_at=last_read_at,
            last_quality_state=last_quality_state,
            is_active=is_active,
            notes=notes,
            created_at=now,
            updated_at=now,
            version=1,
        )


@dataclass
class MaintenanceSensorReading:
    id: str
    organization_id: str
    sensor_id: str
    reading_value: Decimal
    reading_unit: str
    reading_timestamp: datetime
    quality_state: MaintenanceSensorQualityState = MaintenanceSensorQualityState.VALID
    source_name: str = ""
    source_batch_id: str = ""
    received_at: datetime | None = None
    raw_payload_ref: str = ""
    created_at: datetime | None = None
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        sensor_id: str,
        reading_value: Decimal,
        reading_unit: str,
        reading_timestamp: datetime,
        quality_state: MaintenanceSensorQualityState = MaintenanceSensorQualityState.VALID,
        source_name: str = "",
        source_batch_id: str = "",
        received_at: datetime | None = None,
        raw_payload_ref: str = "",
    ) -> "MaintenanceSensorReading":
        now = datetime.now(timezone.utc)
        return MaintenanceSensorReading(
            id=generate_id(),
            organization_id=organization_id,
            sensor_id=sensor_id,
            reading_value=reading_value,
            reading_unit=reading_unit,
            reading_timestamp=reading_timestamp,
            quality_state=quality_state,
            source_name=source_name,
            source_batch_id=source_batch_id,
            received_at=received_at or now,
            raw_payload_ref=raw_payload_ref,
            created_at=now,
            version=1,
        )


@validated_dataclass
class MaintenanceIntegrationSource:
    id: str
    organization_id: str
    integration_code: str
    name: str
    integration_type: str
    endpoint_or_path: str = ""
    authentication_mode: str = ""
    schedule_expression: str = ""
    last_successful_sync_at: datetime | None = None
    last_failed_sync_at: datetime | None = None
    last_error_message: str = ""
    is_active: bool = True
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @field_validator("id", "organization_id", mode="before")
    @classmethod
    def _validate_required_ids(cls, value: object, info) -> str:
        messages = {
            "id": (
                "Maintenance integration source ID is required.",
                "MAINTENANCE_INTEGRATION_SOURCE_ID_REQUIRED",
            ),
            "organization_id": (
                "Organization ID is required.",
                "MAINTENANCE_INTEGRATION_SOURCE_ORGANIZATION_REQUIRED",
            ),
        }
        message, code = messages[info.field_name]
        return normalize_required_text(value, message=message, code=code)

    @field_validator("integration_code", mode="before")
    @classmethod
    def _validate_integration_code(cls, value: object) -> str:
        return normalize_maintenance_code(value, label="Integration code")

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: object) -> str:
        return normalize_maintenance_name(value, label="Integration name")

    @field_validator("integration_type", mode="before")
    @classmethod
    def _validate_integration_type(cls, value: object) -> str:
        return normalize_maintenance_name(value, label="Integration type").upper()

    @field_validator(
        "endpoint_or_path",
        "schedule_expression",
        "last_error_message",
        "notes",
        mode="before",
    )
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("authentication_mode", mode="before")
    @classmethod
    def _normalize_authentication_mode(cls, value: object) -> str:
        return normalize_optional_upper_text(value)

    @field_validator(
        "last_successful_sync_at",
        "last_failed_sync_at",
        "created_at",
        "updated_at",
        mode="before",
    )
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime | None:
        return normalize_optional_datetime(
            value,
            message=f"Maintenance integration source {info.field_name.replace('_', ' ')} is invalid.",
            code=f"MAINTENANCE_INTEGRATION_SOURCE_{info.field_name.upper()}_INVALID",
        )

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Maintenance integration source version must be positive.",
            code="MAINTENANCE_INTEGRATION_SOURCE_VERSION_INVALID",
        )

    @model_validator(mode="after")
    def _validate_ranges(self) -> "MaintenanceIntegrationSource":
        if (
            self.updated_at is not None
            and self.created_at is not None
            and self.updated_at < self.created_at
        ):
            raise ValidationError(
                "Updated timestamp cannot be earlier than created timestamp.",
                code="MAINTENANCE_INTEGRATION_SOURCE_UPDATED_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        *,
        organization_id: str,
        integration_code: str,
        name: str,
        integration_type: str,
        endpoint_or_path: str = "",
        authentication_mode: str = "",
        schedule_expression: str = "",
        is_active: bool = True,
        notes: str = "",
    ) -> "MaintenanceIntegrationSource":
        now = datetime.now(timezone.utc)
        return MaintenanceIntegrationSource(
            id=generate_id(),
            organization_id=organization_id,
            integration_code=integration_code,
            name=name,
            integration_type=integration_type,
            endpoint_or_path=endpoint_or_path,
            authentication_mode=authentication_mode,
            schedule_expression=schedule_expression,
            last_successful_sync_at=None,
            last_failed_sync_at=None,
            last_error_message="",
            is_active=is_active,
            notes=notes,
            created_at=now,
            updated_at=now,
            version=1,
        )


@validated_dataclass
class MaintenanceSensorSourceMapping:
    id: str
    organization_id: str
    integration_source_id: str
    sensor_id: str
    external_equipment_key: str = ""
    external_measurement_key: str = ""
    transform_rule: str = ""
    unit_conversion_rule: str = ""
    is_active: bool = True
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @field_validator(
        "id",
        "organization_id",
        "integration_source_id",
        "sensor_id",
        mode="before",
    )
    @classmethod
    def _validate_required_ids(cls, value: object, info) -> str:
        messages = {
            "id": (
                "Maintenance sensor source mapping ID is required.",
                "MAINTENANCE_SENSOR_SOURCE_MAPPING_ID_REQUIRED",
            ),
            "organization_id": (
                "Organization ID is required.",
                "MAINTENANCE_SENSOR_SOURCE_MAPPING_ORGANIZATION_REQUIRED",
            ),
            "integration_source_id": (
                "Integration source ID is required.",
                "MAINTENANCE_SENSOR_SOURCE_MAPPING_INTEGRATION_SOURCE_REQUIRED",
            ),
            "sensor_id": (
                "Sensor ID is required.",
                "MAINTENANCE_SENSOR_SOURCE_MAPPING_SENSOR_REQUIRED",
            ),
        }
        message, code = messages[info.field_name]
        return normalize_required_text(value, message=message, code=code)

    @field_validator("external_equipment_key", "transform_rule", "unit_conversion_rule", "notes", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("external_measurement_key", mode="before")
    @classmethod
    def _validate_external_measurement_key(cls, value: object) -> str:
        return normalize_maintenance_name(value, label="External measurement key")

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime | None:
        return normalize_optional_datetime(
            value,
            message=f"Maintenance sensor source mapping {info.field_name.replace('_', ' ')} is invalid.",
            code=f"MAINTENANCE_SENSOR_SOURCE_MAPPING_{info.field_name.upper()}_INVALID",
        )

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Maintenance sensor source mapping version must be positive.",
            code="MAINTENANCE_SENSOR_SOURCE_MAPPING_VERSION_INVALID",
        )

    @model_validator(mode="after")
    def _validate_ranges(self) -> "MaintenanceSensorSourceMapping":
        if (
            self.updated_at is not None
            and self.created_at is not None
            and self.updated_at < self.created_at
        ):
            raise ValidationError(
                "Updated timestamp cannot be earlier than created timestamp.",
                code="MAINTENANCE_SENSOR_SOURCE_MAPPING_UPDATED_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        *,
        organization_id: str,
        integration_source_id: str,
        sensor_id: str,
        external_equipment_key: str = "",
        external_measurement_key: str = "",
        transform_rule: str = "",
        unit_conversion_rule: str = "",
        is_active: bool = True,
        notes: str = "",
    ) -> "MaintenanceSensorSourceMapping":
        now = datetime.now(timezone.utc)
        return MaintenanceSensorSourceMapping(
            id=generate_id(),
            organization_id=organization_id,
            integration_source_id=integration_source_id,
            sensor_id=sensor_id,
            external_equipment_key=external_equipment_key,
            external_measurement_key=external_measurement_key,
            transform_rule=transform_rule,
            unit_conversion_rule=unit_conversion_rule,
            is_active=is_active,
            notes=notes,
            created_at=now,
            updated_at=now,
            version=1,
        )


@validated_dataclass
class MaintenanceSensorException:
    id: str
    organization_id: str
    sensor_id: str | None = None
    integration_source_id: str | None = None
    source_mapping_id: str | None = None
    exception_type: MaintenanceSensorExceptionType = MaintenanceSensorExceptionType.STALE_READING
    status: MaintenanceSensorExceptionStatus = MaintenanceSensorExceptionStatus.OPEN
    message: str = ""
    source_batch_id: str = ""
    raw_payload_ref: str = ""
    detected_at: datetime | None = None
    acknowledged_at: datetime | None = None
    acknowledged_by_user_id: str | None = None
    resolved_at: datetime | None = None
    resolved_by_user_id: str | None = None
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @field_validator("id", "organization_id", mode="before")
    @classmethod
    def _validate_required_ids(cls, value: object, info) -> str:
        messages = {
            "id": (
                "Maintenance sensor exception ID is required.",
                "MAINTENANCE_SENSOR_EXCEPTION_ID_REQUIRED",
            ),
            "organization_id": (
                "Organization ID is required.",
                "MAINTENANCE_SENSOR_EXCEPTION_ORGANIZATION_REQUIRED",
            ),
        }
        message, code = messages[info.field_name]
        return normalize_required_text(value, message=message, code=code)

    @field_validator(
        "sensor_id",
        "integration_source_id",
        "source_mapping_id",
        "acknowledged_by_user_id",
        "resolved_by_user_id",
        mode="before",
    )
    @classmethod
    def _normalize_optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("exception_type", mode="before")
    @classmethod
    def _validate_exception_type(cls, value: object) -> MaintenanceSensorExceptionType:
        return normalize_sensor_exception_type(value)

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, value: object) -> MaintenanceSensorExceptionStatus:
        return normalize_sensor_exception_status(value)

    @field_validator("message", mode="before")
    @classmethod
    def _validate_message(cls, value: object) -> str:
        return normalize_maintenance_name(value, label="Exception message")

    @field_validator("source_batch_id", "raw_payload_ref", "notes", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator(
        "detected_at",
        "acknowledged_at",
        "resolved_at",
        "created_at",
        "updated_at",
        mode="before",
    )
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime | None:
        return normalize_optional_datetime(
            value,
            message=f"Maintenance sensor exception {info.field_name.replace('_', ' ')} is invalid.",
            code=f"MAINTENANCE_SENSOR_EXCEPTION_{info.field_name.upper()}_INVALID",
        )

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Maintenance sensor exception version must be positive.",
            code="MAINTENANCE_SENSOR_EXCEPTION_VERSION_INVALID",
        )

    @model_validator(mode="after")
    def _validate_ranges(self) -> "MaintenanceSensorException":
        if (
            self.acknowledged_at is not None
            and self.detected_at is not None
            and self.acknowledged_at < self.detected_at
        ):
            raise ValidationError(
                "Acknowledged timestamp cannot be earlier than detected timestamp.",
                code="MAINTENANCE_SENSOR_EXCEPTION_ACKNOWLEDGED_RANGE_INVALID",
            )
        if (
            self.resolved_at is not None
            and self.detected_at is not None
            and self.resolved_at < self.detected_at
        ):
            raise ValidationError(
                "Resolved timestamp cannot be earlier than detected timestamp.",
                code="MAINTENANCE_SENSOR_EXCEPTION_RESOLVED_RANGE_INVALID",
            )
        if (
            self.resolved_at is not None
            and self.acknowledged_at is not None
            and self.resolved_at < self.acknowledged_at
        ):
            raise ValidationError(
                "Resolved timestamp cannot be earlier than acknowledged timestamp.",
                code="MAINTENANCE_SENSOR_EXCEPTION_RESOLVED_RANGE_INVALID",
            )
        if (
            self.updated_at is not None
            and self.created_at is not None
            and self.updated_at < self.created_at
        ):
            raise ValidationError(
                "Updated timestamp cannot be earlier than created timestamp.",
                code="MAINTENANCE_SENSOR_EXCEPTION_UPDATED_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        *,
        organization_id: str,
        sensor_id: str | None = None,
        integration_source_id: str | None = None,
        source_mapping_id: str | None = None,
        exception_type: MaintenanceSensorExceptionType | str,
        message: str,
        source_batch_id: str = "",
        raw_payload_ref: str = "",
        detected_at: datetime | str | None = None,
        notes: str = "",
    ) -> "MaintenanceSensorException":
        now = datetime.now(timezone.utc)
        return MaintenanceSensorException(
            id=generate_id(),
            organization_id=organization_id,
            sensor_id=sensor_id,
            integration_source_id=integration_source_id,
            source_mapping_id=source_mapping_id,
            exception_type=exception_type,
            status=MaintenanceSensorExceptionStatus.OPEN,
            message=message,
            source_batch_id=source_batch_id,
            raw_payload_ref=raw_payload_ref,
            detected_at=detected_at or now,
            acknowledged_at=None,
            acknowledged_by_user_id=None,
            resolved_at=None,
            resolved_by_user_id=None,
            notes=notes,
            created_at=now,
            updated_at=now,
            version=1,
        )


__all__ = [
    "MaintenanceDowntimeEvent",
    "MaintenanceFailureCode",
    "MaintenanceIntegrationSource",
    "MaintenanceSensor",
    "MaintenanceSensorException",
    "MaintenanceSensorReading",
    "MaintenanceSensorSourceMapping",
]
