from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.modules.maintenance_management.domain import MaintenanceIntegrationSource
from core.modules.maintenance_management.interfaces import MaintenanceIntegrationSourceRepository
from core.modules.maintenance_management.support import (
    coerce_optional_datetime,
    normalize_maintenance_code,
    normalize_maintenance_name,
    normalize_optional_text,
)
from src.core.platform.audit.helpers import record_audit
from src.core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.org.contracts import OrganizationRepository
from src.core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from src.core.platform.org.domain import Organization


class MaintenanceIntegrationSourceService:
    def __init__(
        self,
        session: Session,
        integration_source_repo: MaintenanceIntegrationSourceRepository,
        *,
        organization_repo: OrganizationRepository,
        sensor_exception_service=None,
        user_session=None,
        audit_service=None,
    ) -> None:
        self._session = session
        self._integration_source_repo = integration_source_repo
        self._organization_repo = organization_repo
        self._sensor_exception_service = sensor_exception_service
        self._user_session = user_session
        self._audit_service = audit_service

    def list_sources(
        self,
        *,
        active_only: bool | None = None,
        integration_type: str | None = None,
    ) -> list[MaintenanceIntegrationSource]:
        self._require_read("list maintenance integration sources")
        self._ensure_not_scope_restricted("list maintenance integration sources")
        organization = self._active_organization()
        return self._integration_source_repo.list_for_organization(
            organization.id,
            active_only=active_only,
            integration_type=normalize_optional_text(integration_type).upper() or None,
        )

    def search_sources(
        self,
        *,
        search_text: str = "",
        active_only: bool | None = True,
        integration_type: str | None = None,
    ) -> list[MaintenanceIntegrationSource]:
        normalized_search = normalize_optional_text(search_text).lower()
        rows = self.list_sources(active_only=active_only, integration_type=integration_type)
        if not normalized_search:
            return rows
        return [
            row
            for row in rows
            if normalized_search in " ".join(
                filter(
                    None,
                    [
                        row.integration_code,
                        row.name,
                        row.integration_type,
                        row.endpoint_or_path,
                        row.authentication_mode,
                        row.schedule_expression,
                        row.last_error_message,
                    ],
                )
            ).lower()
        ]

    def get_source(self, integration_source_id: str) -> MaintenanceIntegrationSource:
        self._require_read("view maintenance integration source")
        self._ensure_not_scope_restricted("view maintenance integration source")
        return self._get_source(integration_source_id, organization=self._active_organization())

    def find_source_by_code(
        self,
        integration_code: str,
        *,
        active_only: bool | None = None,
    ) -> MaintenanceIntegrationSource | None:
        self._require_read("resolve maintenance integration source")
        self._ensure_not_scope_restricted("resolve maintenance integration source")
        organization = self._active_organization()
        source = self._integration_source_repo.get_by_code(
            organization.id,
            normalize_maintenance_code(integration_code, label="Integration code"),
        )
        if source is None:
            return None
        if active_only is not None and source.is_active != bool(active_only):
            return None
        return source

    def create_source(
        self,
        *,
        integration_code: str,
        name: str,
        integration_type: str,
        endpoint_or_path: str = "",
        authentication_mode: str = "",
        schedule_expression: str = "",
        is_active: bool = True,
        notes: str = "",
    ) -> MaintenanceIntegrationSource:
        self._require_manage("create maintenance integration source")
        self._ensure_not_scope_restricted("create maintenance integration source")
        organization = self._active_organization()
        normalized_code = normalize_maintenance_code(integration_code, label="Integration code")
        if self._integration_source_repo.get_by_code(organization.id, normalized_code) is not None:
            raise ValidationError(
                "Integration code already exists in the active organization.",
                code="MAINTENANCE_INTEGRATION_SOURCE_CODE_EXISTS",
            )
        source = MaintenanceIntegrationSource.create(
            organization_id=organization.id,
            integration_code=normalized_code,
            name=normalize_maintenance_name(name, label="Integration name"),
            integration_type=normalize_maintenance_name(integration_type, label="Integration type").upper(),
            endpoint_or_path=normalize_optional_text(endpoint_or_path),
            authentication_mode=normalize_optional_text(authentication_mode).upper(),
            schedule_expression=normalize_optional_text(schedule_expression),
            is_active=bool(is_active),
            notes=normalize_optional_text(notes),
        )
        try:
            self._integration_source_repo.add(source)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Integration code already exists in the active organization.",
                code="MAINTENANCE_INTEGRATION_SOURCE_CODE_EXISTS",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_integration_source.create", source)
        return source

    def update_source(
        self,
        integration_source_id: str,
        *,
        integration_code: str | None = None,
        name: str | None = None,
        integration_type: str | None = None,
        endpoint_or_path: str | None = None,
        authentication_mode: str | None = None,
        schedule_expression: str | None = None,
        last_successful_sync_at=None,
        last_failed_sync_at=None,
        last_error_message: str | None = None,
        is_active: bool | None = None,
        notes: str | None = None,
        expected_version: int | None = None,
    ) -> MaintenanceIntegrationSource:
        self._require_manage("update maintenance integration source")
        self._ensure_not_scope_restricted("update maintenance integration source")
        organization = self._active_organization()
        source = self._get_source(integration_source_id, organization=organization)
        if expected_version is not None and source.version != expected_version:
            raise ConcurrencyError(
                "Maintenance integration source changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        if integration_code is not None:
            normalized_code = normalize_maintenance_code(integration_code, label="Integration code")
            existing = self._integration_source_repo.get_by_code(organization.id, normalized_code)
            if existing is not None and existing.id != source.id:
                raise ValidationError(
                    "Integration code already exists in the active organization.",
                    code="MAINTENANCE_INTEGRATION_SOURCE_CODE_EXISTS",
                )
            source.integration_code = normalized_code
        if name is not None:
            source.name = normalize_maintenance_name(name, label="Integration name")
        if integration_type is not None:
            source.integration_type = normalize_maintenance_name(integration_type, label="Integration type").upper()
        if endpoint_or_path is not None:
            source.endpoint_or_path = normalize_optional_text(endpoint_or_path)
        if authentication_mode is not None:
            source.authentication_mode = normalize_optional_text(authentication_mode).upper()
        if schedule_expression is not None:
            source.schedule_expression = normalize_optional_text(schedule_expression)
        if last_successful_sync_at is not None:
            source.last_successful_sync_at = coerce_optional_datetime(last_successful_sync_at, label="Last successful sync at")
        if last_failed_sync_at is not None:
            source.last_failed_sync_at = coerce_optional_datetime(last_failed_sync_at, label="Last failed sync at")
        if last_error_message is not None:
            source.last_error_message = normalize_optional_text(last_error_message)
        if is_active is not None:
            source.is_active = bool(is_active)
        if notes is not None:
            source.notes = normalize_optional_text(notes)
        source.updated_at = datetime.now(timezone.utc)
        try:
            self._integration_source_repo.update(source)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Integration code already exists in the active organization.",
                code="MAINTENANCE_INTEGRATION_SOURCE_CODE_EXISTS",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_integration_source.update", source)
        return source

    def record_sync_success(
        self,
        integration_source_id: str,
        *,
        completed_at=None,
        expected_version: int | None = None,
    ) -> MaintenanceIntegrationSource:
        return self.update_source(
            integration_source_id,
            last_successful_sync_at=completed_at or datetime.now(timezone.utc),
            last_failed_sync_at="",
            last_error_message="",
            expected_version=expected_version,
        )

    def record_sync_failure(
        self,
        integration_source_id: str,
        *,
        failed_at=None,
        error_message: str,
        expected_version: int | None = None,
    ) -> MaintenanceIntegrationSource:
        updated = self.update_source(
            integration_source_id,
            last_failed_sync_at=failed_at or datetime.now(timezone.utc),
            last_error_message=error_message,
            expected_version=expected_version,
        )
        if self._sensor_exception_service is not None:
            self._sensor_exception_service.raise_exception(
                integration_source_id=integration_source_id,
                exception_type="EXTERNAL_SYNC_FAILURE",
                message=error_message,
                detected_at=updated.last_failed_sync_at,
            )
        return updated

    def _record_change(self, action: str, source: MaintenanceIntegrationSource) -> None:
        record_audit(
            self,
            action=action,
            entity_type="maintenance_integration_source",
            entity_id=source.id,
            details={
                "organization_id": source.organization_id,
                "integration_code": source.integration_code,
                "integration_type": source.integration_type,
                "endpoint_or_path": source.endpoint_or_path,
                "authentication_mode": source.authentication_mode,
                "schedule_expression": source.schedule_expression,
                "last_successful_sync_at": source.last_successful_sync_at.isoformat()
                if source.last_successful_sync_at
                else "",
                "last_failed_sync_at": source.last_failed_sync_at.isoformat()
                if source.last_failed_sync_at
                else "",
            },
        )
        domain_events.domain_changed.emit(
            DomainChangeEvent(
                category="module",
                scope_code="maintenance_management",
                entity_type="maintenance_integration_source",
                entity_id=source.id,
                source_event="maintenance_integration_sources_changed",
            )
        )

    def _get_source(
        self,
        integration_source_id: str,
        *,
        organization: Organization,
    ) -> MaintenanceIntegrationSource:
        source = self._integration_source_repo.get(integration_source_id)
        if source is None or source.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance integration source not found in the active organization.",
                code="MAINTENANCE_INTEGRATION_SOURCE_NOT_FOUND",
            )
        return source

    def _ensure_not_scope_restricted(self, operation_label: str) -> None:
        if self._user_session is not None and self._user_session.is_scope_restricted("maintenance"):
            raise BusinessRuleError(
                f"Permission denied for {operation_label}. Shared integration sources require organization-wide maintenance access.",
                code="PERMISSION_DENIED",
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


__all__ = ["MaintenanceIntegrationSourceService"]
