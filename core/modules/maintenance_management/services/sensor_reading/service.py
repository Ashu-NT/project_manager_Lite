from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from core.modules.maintenance_management.domain import MaintenanceSensor, MaintenanceSensorReading
from core.modules.maintenance_management.interfaces import (
    MaintenanceAssetComponentRepository,
    MaintenanceSensorReadingRepository,
    MaintenanceSensorRepository,
)
from core.modules.maintenance_management.support import (
    coerce_decimal_value,
    coerce_optional_datetime,
    coerce_sensor_quality_state,
    normalize_optional_text,
)
from core.platform.access.authorization import filter_scope_rows, require_scope_permission
from core.platform.audit.helpers import record_audit
from core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError
from core.platform.common.interfaces import OrganizationRepository
from core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from core.platform.org.domain import Organization


class MaintenanceSensorReadingService:
    def __init__(
        self,
        session: Session,
        sensor_reading_repo: MaintenanceSensorReadingRepository,
        *,
        organization_repo: OrganizationRepository,
        sensor_repo: MaintenanceSensorRepository,
        component_repo: MaintenanceAssetComponentRepository,
        user_session=None,
        audit_service=None,
    ) -> None:
        self._session = session
        self._sensor_reading_repo = sensor_reading_repo
        self._organization_repo = organization_repo
        self._sensor_repo = sensor_repo
        self._component_repo = component_repo
        self._user_session = user_session
        self._audit_service = audit_service

    def list_readings(
        self,
        *,
        sensor_id: str | None = None,
        quality_state: str | None = None,
        source_batch_id: str | None = None,
        reading_from=None,
        reading_to=None,
    ) -> list[MaintenanceSensorReading]:
        self._require_read("list maintenance sensor readings")
        organization = self._active_organization()
        if sensor_id is not None:
            sensor = self._get_sensor(sensor_id, organization=organization)
            self._require_scope_read(self._scope_anchor_for(sensor), operation_label="list maintenance sensor readings")
        rows = self._sensor_reading_repo.list_for_organization(
            organization.id,
            sensor_id=sensor_id,
            quality_state=normalize_optional_text(quality_state).upper() or None,
            source_batch_id=normalize_optional_text(source_batch_id) or None,
            reading_from=coerce_optional_datetime(reading_from, label="Reading from"),
            reading_to=coerce_optional_datetime(reading_to, label="Reading to"),
        )
        return filter_scope_rows(
            rows,
            self._user_session,
            scope_type="maintenance",
            permission_code="maintenance.read",
            scope_id_getter=lambda row: self._scope_anchor_for_sensor_id(row.sensor_id),
        )

    def get_reading(self, sensor_reading_id: str) -> MaintenanceSensorReading:
        self._require_read("view maintenance sensor reading")
        organization = self._active_organization()
        reading = self._sensor_reading_repo.get(sensor_reading_id)
        if reading is None or reading.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance sensor reading not found in the active organization.",
                code="MAINTENANCE_SENSOR_READING_NOT_FOUND",
            )
        self._require_scope_read(
            self._scope_anchor_for_sensor_id(reading.sensor_id),
            operation_label="view maintenance sensor reading",
        )
        return reading

    def record_reading(
        self,
        *,
        sensor_id: str,
        reading_value,
        reading_unit: str = "",
        reading_timestamp=None,
        quality_state=None,
        source_name: str = "",
        source_batch_id: str = "",
        received_at=None,
        raw_payload_ref: str = "",
    ) -> MaintenanceSensorReading:
        self._require_manage("record maintenance sensor reading")
        organization = self._active_organization()
        sensor = self._get_sensor(sensor_id, organization=organization)
        if not sensor.is_active:
            raise ValidationError(
                "Cannot record a reading against an inactive maintenance sensor.",
                code="MAINTENANCE_SENSOR_INACTIVE",
            )
        scope_id = self._scope_anchor_for(sensor)
        self._require_scope_manage(scope_id, operation_label="record maintenance sensor reading")

        normalized_unit = normalize_optional_text(reading_unit).upper() or sensor.unit
        if not normalized_unit:
            raise ValidationError(
                "Reading unit is required when the sensor does not already define one.",
                code="MAINTENANCE_SENSOR_READING_UNIT_REQUIRED",
            )
        if sensor.unit and normalized_unit != sensor.unit:
            raise ValidationError(
                "Reading unit must match the configured maintenance sensor unit.",
                code="MAINTENANCE_SENSOR_READING_UNIT_MISMATCH",
            )

        resolved_timestamp = coerce_optional_datetime(reading_timestamp, label="Reading timestamp") or datetime.now(timezone.utc)
        resolved_received_at = coerce_optional_datetime(received_at, label="Received at") or datetime.now(timezone.utc)
        resolved_quality = coerce_sensor_quality_state(quality_state)
        reading = MaintenanceSensorReading.create(
            organization_id=organization.id,
            sensor_id=sensor.id,
            reading_value=coerce_decimal_value(reading_value, label="Reading value"),
            reading_unit=normalized_unit,
            reading_timestamp=resolved_timestamp,
            quality_state=resolved_quality,
            source_name=normalize_optional_text(source_name),
            source_batch_id=normalize_optional_text(source_batch_id),
            received_at=resolved_received_at,
            raw_payload_ref=normalize_optional_text(raw_payload_ref),
        )

        should_refresh_snapshot = sensor.last_read_at is None or resolved_timestamp >= sensor.last_read_at
        if should_refresh_snapshot:
            sensor.current_value = reading.reading_value
            sensor.unit = normalized_unit
            sensor.last_read_at = resolved_timestamp
            sensor.last_quality_state = resolved_quality
            sensor.updated_at = datetime.now(timezone.utc)

        try:
            self._sensor_reading_repo.add(reading)
            if should_refresh_snapshot:
                self._sensor_repo.update(sensor)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_sensor_reading.create", reading)
        if should_refresh_snapshot:
            domain_events.domain_changed.emit(
                DomainChangeEvent(
                    category="module",
                    scope_code="maintenance_management",
                    entity_type="maintenance_sensor",
                    entity_id=sensor.id,
                    source_event="maintenance_sensors_changed",
                )
            )
        return reading

    def _scope_anchor_for_sensor_id(self, sensor_id: str) -> str:
        sensor = self._sensor_repo.get(sensor_id)
        if sensor is None:
            return ""
        return self._scope_anchor_for(sensor)

    def _scope_anchor_for(self, sensor: MaintenanceSensor) -> str:
        if sensor.asset_id:
            return sensor.asset_id
        if sensor.component_id:
            component = self._component_repo.get(sensor.component_id)
            if component is not None and component.asset_id:
                return component.asset_id
        if sensor.system_id:
            return sensor.system_id
        return ""

    def _require_scope_read(self, scope_id: str, *, operation_label: str) -> None:
        if scope_id:
            require_scope_permission(
                self._user_session,
                "maintenance",
                scope_id,
                "maintenance.read",
                operation_label=operation_label,
            )
            return
        if self._user_session is not None and self._user_session.is_scope_restricted("maintenance"):
            raise BusinessRuleError(
                f"Permission denied for {operation_label}. The record is not anchored to a maintenance scope grant.",
                code="PERMISSION_DENIED",
            )

    def _require_scope_manage(self, scope_id: str, *, operation_label: str) -> None:
        if scope_id:
            require_scope_permission(
                self._user_session,
                "maintenance",
                scope_id,
                "maintenance.manage",
                operation_label=operation_label,
            )
            return
        if self._user_session is not None and self._user_session.is_scope_restricted("maintenance"):
            raise BusinessRuleError(
                f"Permission denied for {operation_label}. The record is not anchored to a maintenance scope grant.",
                code="PERMISSION_DENIED",
            )

    def _record_change(self, action: str, reading: MaintenanceSensorReading) -> None:
        record_audit(
            self,
            action=action,
            entity_type="maintenance_sensor_reading",
            entity_id=reading.id,
            details={
                "organization_id": reading.organization_id,
                "sensor_id": reading.sensor_id,
                "reading_value": str(reading.reading_value),
                "reading_unit": reading.reading_unit,
                "reading_timestamp": reading.reading_timestamp.isoformat(),
                "quality_state": reading.quality_state.value,
                "source_name": reading.source_name,
                "source_batch_id": reading.source_batch_id,
                "raw_payload_ref": reading.raw_payload_ref,
            },
        )
        domain_events.domain_changed.emit(
            DomainChangeEvent(
                category="module",
                scope_code="maintenance_management",
                entity_type="maintenance_sensor_reading",
                entity_id=reading.id,
                source_event="maintenance_sensor_readings_changed",
            )
        )

    def _get_sensor(self, sensor_id: str, *, organization: Organization) -> MaintenanceSensor:
        sensor = self._sensor_repo.get(sensor_id)
        if sensor is None or sensor.organization_id != organization.id:
            raise NotFoundError("Maintenance sensor not found in the active organization.", code="MAINTENANCE_SENSOR_NOT_FOUND")
        return sensor

    def _active_organization(self) -> Organization:
        organization = self._organization_repo.get_active()
        if organization is None:
            raise BusinessRuleError("No active organization selected.", code="NO_ACTIVE_ORGANIZATION")
        return organization

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.read", operation_label=operation_label)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.manage", operation_label=operation_label)


__all__ = ["MaintenanceSensorReadingService"]
