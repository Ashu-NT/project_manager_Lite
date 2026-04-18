from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.modules.maintenance_management.domain import (
    MaintenanceSensorException,
    MaintenanceSensorExceptionStatus,
)
from core.modules.maintenance_management.interfaces import (
    MaintenanceIntegrationSourceRepository,
    MaintenanceSensorExceptionRepository,
    MaintenanceSensorRepository,
    MaintenanceSensorSourceMappingRepository,
)
from core.modules.maintenance_management.support import (
    coerce_optional_datetime,
    coerce_sensor_exception_status,
    coerce_sensor_exception_type,
    normalize_maintenance_name,
    normalize_optional_text,
)
from src.core.platform.access.authorization import filter_scope_rows, require_scope_permission
from core.platform.audit.helpers import record_audit
from src.core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.org.contracts import OrganizationRepository
from src.core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from src.core.platform.org.domain import Organization


class MaintenanceSensorExceptionService:
    def __init__(
        self,
        session: Session,
        sensor_exception_repo: MaintenanceSensorExceptionRepository,
        *,
        organization_repo: OrganizationRepository,
        sensor_repo: MaintenanceSensorRepository,
        integration_source_repo: MaintenanceIntegrationSourceRepository,
        sensor_source_mapping_repo: MaintenanceSensorSourceMappingRepository,
        user_session=None,
        audit_service=None,
    ) -> None:
        self._session = session
        self._sensor_exception_repo = sensor_exception_repo
        self._organization_repo = organization_repo
        self._sensor_repo = sensor_repo
        self._integration_source_repo = integration_source_repo
        self._sensor_source_mapping_repo = sensor_source_mapping_repo
        self._user_session = user_session
        self._audit_service = audit_service

    def list_exceptions(
        self,
        *,
        sensor_id: str | None = None,
        integration_source_id: str | None = None,
        source_mapping_id: str | None = None,
        exception_type: str | None = None,
        status: str | None = None,
        source_batch_id: str | None = None,
    ) -> list[MaintenanceSensorException]:
        self._require_read("list maintenance sensor exceptions")
        organization = self._active_organization()
        if sensor_id is not None:
            self._require_scope_read(
                self._scope_anchor_for_sensor_id(sensor_id),
                operation_label="list maintenance sensor exceptions",
            )
        if integration_source_id is not None:
            self._get_integration_source(integration_source_id, organization=organization)
        if source_mapping_id is not None:
            self._get_source_mapping(source_mapping_id, organization=organization)
        rows = self._sensor_exception_repo.list_for_organization(
            organization.id,
            sensor_id=sensor_id,
            integration_source_id=integration_source_id,
            source_mapping_id=source_mapping_id,
            exception_type=normalize_optional_text(exception_type).upper() or None,
            status=normalize_optional_text(status).upper() or None,
            source_batch_id=normalize_optional_text(source_batch_id) or None,
        )
        return filter_scope_rows(
            rows,
            self._user_session,
            scope_type="maintenance",
            permission_code="maintenance.read",
            scope_id_getter=self._scope_anchor_for,
        )

    def get_exception(self, sensor_exception_id: str) -> MaintenanceSensorException:
        self._require_read("view maintenance sensor exception")
        exception = self._get_exception(sensor_exception_id, organization=self._active_organization())
        self._require_scope_or_org_read(exception, operation_label="view maintenance sensor exception")
        return exception

    def raise_exception(
        self,
        *,
        exception_type,
        message: str,
        sensor_id: str | None = None,
        integration_source_id: str | None = None,
        source_mapping_id: str | None = None,
        source_batch_id: str = "",
        raw_payload_ref: str = "",
        detected_at=None,
        notes: str = "",
    ) -> MaintenanceSensorException:
        self._require_manage("create maintenance sensor exception")
        organization = self._active_organization()
        sensor_id, integration_source_id, source_mapping_id = self._resolve_context(
            organization=organization,
            sensor_id=sensor_id,
            integration_source_id=integration_source_id,
            source_mapping_id=source_mapping_id,
            operation_label="create maintenance sensor exception",
        )
        exception = MaintenanceSensorException.create(
            organization_id=organization.id,
            sensor_id=sensor_id,
            integration_source_id=integration_source_id,
            source_mapping_id=source_mapping_id,
            exception_type=coerce_sensor_exception_type(exception_type),
            message=normalize_maintenance_name(message, label="Exception message"),
            source_batch_id=normalize_optional_text(source_batch_id),
            raw_payload_ref=normalize_optional_text(raw_payload_ref),
            detected_at=coerce_optional_datetime(detected_at, label="Detected at"),
            notes=normalize_optional_text(notes),
        )
        try:
            self._sensor_exception_repo.add(exception)
            self._session.commit()
        except IntegrityError:
            self._session.rollback()
            raise
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_sensor_exception.create", exception)
        return exception

    def update_exception_status(
        self,
        sensor_exception_id: str,
        *,
        status,
        notes: str | None = None,
        expected_version: int | None = None,
    ) -> MaintenanceSensorException:
        self._require_manage("update maintenance sensor exception")
        exception = self.get_exception(sensor_exception_id)
        if expected_version is not None and exception.version != expected_version:
            raise ConcurrencyError(
                "Maintenance sensor exception changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        resolved_status = coerce_sensor_exception_status(status)
        now = datetime.now(timezone.utc)
        current_user_id = self._current_user_id()
        exception.status = resolved_status
        if notes is not None:
            exception.notes = normalize_optional_text(notes)
        if resolved_status == MaintenanceSensorExceptionStatus.ACKNOWLEDGED:
            exception.acknowledged_at = now
            exception.acknowledged_by_user_id = current_user_id
        if resolved_status in {MaintenanceSensorExceptionStatus.RESOLVED, MaintenanceSensorExceptionStatus.IGNORED}:
            if exception.acknowledged_at is None:
                exception.acknowledged_at = now
                exception.acknowledged_by_user_id = current_user_id
            exception.resolved_at = now
            exception.resolved_by_user_id = current_user_id
        exception.updated_at = now
        try:
            self._sensor_exception_repo.update(exception)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_sensor_exception.update", exception)
        return exception

    def resolve_open_integration_sync_failures(
        self,
        integration_source_id: str,
        *,
        expected_open_only: bool = True,
    ) -> None:
        organization = self._active_organization()
        self._get_integration_source(integration_source_id, organization=organization)
        rows = self._sensor_exception_repo.list_for_organization(
            organization.id,
            integration_source_id=integration_source_id,
            exception_type="EXTERNAL_SYNC_FAILURE",
            status="OPEN" if expected_open_only else None,
        )
        if not rows:
            return
        now = datetime.now(timezone.utc)
        current_user_id = self._current_user_id()
        try:
            for row in rows:
                row.status = MaintenanceSensorExceptionStatus.RESOLVED
                row.acknowledged_at = row.acknowledged_at or now
                row.acknowledged_by_user_id = row.acknowledged_by_user_id or current_user_id
                row.resolved_at = now
                row.resolved_by_user_id = current_user_id
                row.updated_at = now
                self._sensor_exception_repo.update(row)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

    def _resolve_context(
        self,
        *,
        organization: Organization,
        sensor_id: str | None,
        integration_source_id: str | None,
        source_mapping_id: str | None,
        operation_label: str,
    ) -> tuple[str | None, str | None, str | None]:
        mapping = self._get_source_mapping(source_mapping_id, organization=organization) if source_mapping_id else None
        sensor = self._get_sensor(sensor_id, organization=organization) if sensor_id else None
        if mapping is not None:
            if sensor is None:
                sensor = self._get_sensor(mapping.sensor_id, organization=organization)
            elif mapping.sensor_id != sensor.id:
                raise ValidationError(
                    "Selected source mapping must belong to the selected maintenance sensor.",
                    code="MAINTENANCE_SENSOR_EXCEPTION_MAPPING_SENSOR_MISMATCH",
                )
            if integration_source_id is None:
                integration_source_id = mapping.integration_source_id
            elif mapping.integration_source_id != integration_source_id:
                raise ValidationError(
                    "Selected source mapping must belong to the selected integration source.",
                    code="MAINTENANCE_SENSOR_EXCEPTION_MAPPING_SOURCE_MISMATCH",
                )
        if integration_source_id is not None:
            self._get_integration_source(integration_source_id, organization=organization)
        if sensor is not None:
            self._require_scope_manage(self._scope_anchor_for_sensor_id(sensor.id), operation_label=operation_label)
            sensor_id = sensor.id
        elif self._user_session is not None and self._user_session.is_scope_restricted("maintenance"):
            raise BusinessRuleError(
                f"Permission denied for {operation_label}. Organization-wide sensor exceptions require broader maintenance access.",
                code="PERMISSION_DENIED",
            )
        if sensor_id is None and integration_source_id is None:
            raise ValidationError(
                "Maintenance sensor exception must be linked to a sensor, source mapping, or integration source.",
                code="MAINTENANCE_SENSOR_EXCEPTION_CONTEXT_REQUIRED",
            )
        return sensor_id, integration_source_id, mapping.id if mapping is not None else source_mapping_id

    def _scope_anchor_for(self, exception: MaintenanceSensorException) -> str:
        if exception.sensor_id:
            return self._scope_anchor_for_sensor_id(exception.sensor_id)
        if exception.source_mapping_id:
            mapping = self._sensor_source_mapping_repo.get(exception.source_mapping_id)
            if mapping is not None:
                return self._scope_anchor_for_sensor_id(mapping.sensor_id)
        return ""

    def _scope_anchor_for_sensor_id(self, sensor_id: str) -> str:
        sensor = self._sensor_repo.get(sensor_id)
        if sensor is None:
            return ""
        if sensor.asset_id:
            return sensor.asset_id
        if sensor.system_id:
            return sensor.system_id
        return ""

    def _require_scope_or_org_read(self, exception: MaintenanceSensorException, *, operation_label: str) -> None:
        scope_id = self._scope_anchor_for(exception)
        if scope_id:
            self._require_scope_read(scope_id, operation_label=operation_label)
            return
        if self._user_session is not None and self._user_session.is_scope_restricted("maintenance"):
            raise BusinessRuleError(
                f"Permission denied for {operation_label}. Organization-wide sensor exceptions require broader maintenance access.",
                code="PERMISSION_DENIED",
            )

    def _record_change(self, action: str, exception: MaintenanceSensorException) -> None:
        record_audit(
            self,
            action=action,
            entity_type="maintenance_sensor_exception",
            entity_id=exception.id,
            details={
                "organization_id": exception.organization_id,
                "sensor_id": exception.sensor_id,
                "integration_source_id": exception.integration_source_id,
                "source_mapping_id": exception.source_mapping_id,
                "exception_type": exception.exception_type.value,
                "status": exception.status.value,
                "source_batch_id": exception.source_batch_id,
            },
        )
        domain_events.domain_changed.emit(
            DomainChangeEvent(
                category="module",
                scope_code="maintenance_management",
                entity_type="maintenance_sensor_exception",
                entity_id=exception.id,
                source_event="maintenance_sensor_exceptions_changed",
            )
        )

    def _get_exception(self, sensor_exception_id: str, *, organization: Organization) -> MaintenanceSensorException:
        exception = self._sensor_exception_repo.get(sensor_exception_id)
        if exception is None or exception.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance sensor exception not found in the active organization.",
                code="MAINTENANCE_SENSOR_EXCEPTION_NOT_FOUND",
            )
        return exception

    def _get_sensor(self, sensor_id: str, *, organization: Organization):
        sensor = self._sensor_repo.get(sensor_id)
        if sensor is None or sensor.organization_id != organization.id:
            raise NotFoundError("Maintenance sensor not found in the active organization.", code="MAINTENANCE_SENSOR_NOT_FOUND")
        return sensor

    def _get_integration_source(self, integration_source_id: str, *, organization: Organization):
        source = self._integration_source_repo.get(integration_source_id)
        if source is None or source.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance integration source not found in the active organization.",
                code="MAINTENANCE_INTEGRATION_SOURCE_NOT_FOUND",
            )
        return source

    def _get_source_mapping(self, source_mapping_id: str | None, *, organization: Organization):
        if not source_mapping_id:
            return None
        mapping = self._sensor_source_mapping_repo.get(source_mapping_id)
        if mapping is None or mapping.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance sensor source mapping not found in the active organization.",
                code="MAINTENANCE_SENSOR_SOURCE_MAPPING_NOT_FOUND",
            )
        return mapping

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

    def _current_user_id(self) -> str | None:
        principal = getattr(self._user_session, "principal", None)
        return getattr(principal, "user_id", None) if principal is not None else None

    def _active_organization(self) -> Organization:
        organization = self._organization_repo.get_active()
        if organization is None:
            raise BusinessRuleError("No active organization selected.", code="NO_ACTIVE_ORGANIZATION")
        return organization

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.read", operation_label=operation_label)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.manage", operation_label=operation_label)


__all__ = ["MaintenanceSensorExceptionService"]
