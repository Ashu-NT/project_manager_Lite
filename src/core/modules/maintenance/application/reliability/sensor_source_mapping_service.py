from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.modules.maintenance_management.domain import MaintenanceSensorSourceMapping
from core.modules.maintenance_management.interfaces import (
    MaintenanceIntegrationSourceRepository,
    MaintenanceSensorRepository,
    MaintenanceSensorSourceMappingRepository,
)
from core.modules.maintenance_management.support import normalize_maintenance_name, normalize_optional_text
from src.core.platform.access.authorization import filter_scope_rows, require_scope_permission
from src.core.platform.audit.helpers import record_audit
from src.core.platform.auth.authorization import require_permission
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.org.contracts import OrganizationRepository
from src.core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from src.core.platform.org.domain import Organization


class MaintenanceSensorSourceMappingService:
    def __init__(
        self,
        session: Session,
        sensor_source_mapping_repo: MaintenanceSensorSourceMappingRepository,
        *,
        organization_repo: OrganizationRepository,
        integration_source_repo: MaintenanceIntegrationSourceRepository,
        sensor_repo: MaintenanceSensorRepository,
        user_session=None,
        audit_service=None,
    ) -> None:
        self._session = session
        self._sensor_source_mapping_repo = sensor_source_mapping_repo
        self._organization_repo = organization_repo
        self._integration_source_repo = integration_source_repo
        self._sensor_repo = sensor_repo
        self._user_session = user_session
        self._audit_service = audit_service

    def list_mappings(
        self,
        *,
        integration_source_id: str | None = None,
        sensor_id: str | None = None,
        active_only: bool | None = None,
    ) -> list[MaintenanceSensorSourceMapping]:
        self._require_read("list maintenance sensor source mappings")
        organization = self._active_organization()
        if integration_source_id is not None:
            self._get_integration_source(integration_source_id, organization=organization)
        if sensor_id is not None:
            sensor = self._get_sensor(sensor_id, organization=organization)
            self._require_scope_read(
                self._scope_anchor_for_sensor_id(sensor.id),
                operation_label="list maintenance sensor source mappings",
            )
        rows = self._sensor_source_mapping_repo.list_for_organization(
            organization.id,
            integration_source_id=integration_source_id,
            sensor_id=sensor_id,
            active_only=active_only,
        )
        return filter_scope_rows(
            rows,
            self._user_session,
            scope_type="maintenance",
            permission_code="maintenance.read",
            scope_id_getter=lambda row: self._scope_anchor_for_sensor_id(getattr(row, "sensor_id", "")),
        )

    def get_mapping(self, sensor_source_mapping_id: str) -> MaintenanceSensorSourceMapping:
        self._require_read("view maintenance sensor source mapping")
        organization = self._active_organization()
        mapping = self._sensor_source_mapping_repo.get(sensor_source_mapping_id)
        if mapping is None or mapping.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance sensor source mapping not found in the active organization.",
                code="MAINTENANCE_SENSOR_SOURCE_MAPPING_NOT_FOUND",
            )
        self._require_scope_read(
            self._scope_anchor_for_sensor_id(mapping.sensor_id),
            operation_label="view maintenance sensor source mapping",
        )
        return mapping

    def create_mapping(
        self,
        *,
        integration_source_id: str,
        sensor_id: str,
        external_equipment_key: str = "",
        external_measurement_key: str,
        transform_rule: str = "",
        unit_conversion_rule: str = "",
        is_active: bool = True,
        notes: str = "",
    ) -> MaintenanceSensorSourceMapping:
        self._require_manage("create maintenance sensor source mapping")
        organization = self._active_organization()
        self._get_integration_source(integration_source_id, organization=organization)
        sensor = self._get_sensor(sensor_id, organization=organization)
        self._require_scope_manage(
            self._scope_anchor_for_sensor_id(sensor.id),
            operation_label="create maintenance sensor source mapping",
        )
        normalized_equipment_key = normalize_optional_text(external_equipment_key)
        normalized_measurement_key = normalize_maintenance_name(
            external_measurement_key,
            label="External measurement key",
        )
        self._ensure_unique_mapping(
            organization_id=organization.id,
            integration_source_id=integration_source_id,
            sensor_id=sensor.id,
            external_equipment_key=normalized_equipment_key,
            external_measurement_key=normalized_measurement_key,
        )
        mapping = MaintenanceSensorSourceMapping.create(
            organization_id=organization.id,
            integration_source_id=integration_source_id,
            sensor_id=sensor.id,
            external_equipment_key=normalized_equipment_key,
            external_measurement_key=normalized_measurement_key,
            transform_rule=normalize_optional_text(transform_rule),
            unit_conversion_rule=normalize_optional_text(unit_conversion_rule),
            is_active=bool(is_active),
            notes=normalize_optional_text(notes),
        )
        try:
            self._sensor_source_mapping_repo.add(mapping)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Maintenance sensor source mapping already exists.",
                code="MAINTENANCE_SENSOR_SOURCE_MAPPING_EXISTS",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_sensor_source_mapping.create", mapping)
        return mapping

    def update_mapping(
        self,
        sensor_source_mapping_id: str,
        *,
        integration_source_id: str | None = None,
        sensor_id: str | None = None,
        external_equipment_key: str | None = None,
        external_measurement_key: str | None = None,
        transform_rule: str | None = None,
        unit_conversion_rule: str | None = None,
        is_active: bool | None = None,
        notes: str | None = None,
        expected_version: int | None = None,
    ) -> MaintenanceSensorSourceMapping:
        self._require_manage("update maintenance sensor source mapping")
        organization = self._active_organization()
        mapping = self.get_mapping(sensor_source_mapping_id)
        if expected_version is not None and mapping.version != expected_version:
            raise ConcurrencyError(
                "Maintenance sensor source mapping changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        if integration_source_id is not None:
            self._get_integration_source(integration_source_id, organization=organization)
            mapping.integration_source_id = integration_source_id
        if sensor_id is not None:
            sensor = self._get_sensor(sensor_id, organization=organization)
            self._require_scope_manage(
                self._scope_anchor_for_sensor_id(sensor.id),
                operation_label="update maintenance sensor source mapping",
            )
            mapping.sensor_id = sensor.id
        if external_equipment_key is not None:
            mapping.external_equipment_key = normalize_optional_text(external_equipment_key)
        if external_measurement_key is not None:
            mapping.external_measurement_key = normalize_maintenance_name(
                external_measurement_key,
                label="External measurement key",
            )
        if transform_rule is not None:
            mapping.transform_rule = normalize_optional_text(transform_rule)
        if unit_conversion_rule is not None:
            mapping.unit_conversion_rule = normalize_optional_text(unit_conversion_rule)
        if is_active is not None:
            mapping.is_active = bool(is_active)
        if notes is not None:
            mapping.notes = normalize_optional_text(notes)
        self._ensure_unique_mapping(
            organization_id=organization.id,
            integration_source_id=mapping.integration_source_id,
            sensor_id=mapping.sensor_id,
            external_equipment_key=mapping.external_equipment_key,
            external_measurement_key=mapping.external_measurement_key,
            self_id=mapping.id,
        )
        mapping.updated_at = datetime.now(timezone.utc)
        try:
            self._sensor_source_mapping_repo.update(mapping)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Maintenance sensor source mapping already exists.",
                code="MAINTENANCE_SENSOR_SOURCE_MAPPING_EXISTS",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_sensor_source_mapping.update", mapping)
        return mapping

    def _ensure_unique_mapping(
        self,
        *,
        organization_id: str,
        integration_source_id: str,
        sensor_id: str,
        external_equipment_key: str,
        external_measurement_key: str,
        self_id: str | None = None,
    ) -> None:
        existing = self._sensor_source_mapping_repo.list_for_organization(
            organization_id,
            integration_source_id=integration_source_id,
            sensor_id=sensor_id,
            active_only=None,
        )
        for row in existing:
            if self_id and row.id == self_id:
                continue
            if (
                row.external_equipment_key == external_equipment_key
                and row.external_measurement_key == external_measurement_key
            ):
                raise ValidationError(
                    "Maintenance sensor source mapping already exists.",
                    code="MAINTENANCE_SENSOR_SOURCE_MAPPING_EXISTS",
                )

    def _record_change(self, action: str, mapping: MaintenanceSensorSourceMapping) -> None:
        record_audit(
            self,
            action=action,
            entity_type="maintenance_sensor_source_mapping",
            entity_id=mapping.id,
            details={
                "organization_id": mapping.organization_id,
                "integration_source_id": mapping.integration_source_id,
                "sensor_id": mapping.sensor_id,
                "external_equipment_key": mapping.external_equipment_key,
                "external_measurement_key": mapping.external_measurement_key,
                "is_active": mapping.is_active,
            },
        )
        domain_events.domain_changed.emit(
            DomainChangeEvent(
                category="module",
                scope_code="maintenance_management",
                entity_type="maintenance_sensor_source_mapping",
                entity_id=mapping.id,
                source_event="maintenance_sensor_source_mappings_changed",
            )
        )

    def _scope_anchor_for_sensor_id(self, sensor_id: str) -> str:
        sensor = self._sensor_repo.get(sensor_id)
        if sensor is None:
            return ""
        if sensor.asset_id:
            return sensor.asset_id
        if sensor.system_id:
            return sensor.system_id
        return ""

    def _get_integration_source(self, integration_source_id: str, *, organization: Organization):
        source = self._integration_source_repo.get(integration_source_id)
        if source is None or source.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance integration source not found in the active organization.",
                code="MAINTENANCE_INTEGRATION_SOURCE_NOT_FOUND",
            )
        return source

    def _get_sensor(self, sensor_id: str, *, organization: Organization):
        sensor = self._sensor_repo.get(sensor_id)
        if sensor is None or sensor.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance sensor not found in the active organization.",
                code="MAINTENANCE_SENSOR_NOT_FOUND",
            )
        return sensor

    def _require_scope_read(self, scope_id: str, *, operation_label: str) -> None:
        if not scope_id and self._user_session is not None and self._user_session.is_scope_restricted("maintenance"):
            raise BusinessRuleError(
                f"Permission denied for {operation_label}. The record is not anchored to a maintenance scope grant.",
                code="PERMISSION_DENIED",
            )
        require_scope_permission(
            self._user_session,
            "maintenance",
            scope_id,
            "maintenance.read",
            operation_label=operation_label,
        )

    def _require_scope_manage(self, scope_id: str, *, operation_label: str) -> None:
        if not scope_id and self._user_session is not None and self._user_session.is_scope_restricted("maintenance"):
            raise BusinessRuleError(
                f"Permission denied for {operation_label}. The record is not anchored to a maintenance scope grant.",
                code="PERMISSION_DENIED",
            )
        require_scope_permission(
            self._user_session,
            "maintenance",
            scope_id,
            "maintenance.manage",
            operation_label=operation_label,
        )

    def _active_organization(self) -> Organization:
        organization = self._organization_repo.get_active()
        if organization is None:
            raise BusinessRuleError("No active organization selected.", code="NO_ACTIVE_ORGANIZATION")
        return organization

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.read", operation_label=operation_label)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.manage", operation_label=operation_label)


__all__ = ["MaintenanceSensorSourceMappingService"]
