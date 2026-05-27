from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from src.core.modules.maintenance.domain.enums import (
    MaintenanceFailureCodeType,
    MaintenanceSensorExceptionStatus,
    MaintenanceSensorExceptionType,
    MaintenanceSensorQualityState,
)
from src.core.platform.common.ids import generate_id


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


@dataclass
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
        current_value: Decimal | None = None,
        last_read_at: datetime | None = None,
        last_quality_state: MaintenanceSensorQualityState = MaintenanceSensorQualityState.VALID,
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


@dataclass
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


@dataclass
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


@dataclass
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

    @staticmethod
    def create(
        *,
        organization_id: str,
        sensor_id: str | None = None,
        integration_source_id: str | None = None,
        source_mapping_id: str | None = None,
        exception_type: MaintenanceSensorExceptionType,
        message: str,
        source_batch_id: str = "",
        raw_payload_ref: str = "",
        detected_at: datetime | None = None,
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
