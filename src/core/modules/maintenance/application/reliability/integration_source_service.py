from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.maintenance.domain import MaintenanceIntegrationSource
from src.core.modules.maintenance.contracts.repositories import MaintenanceIntegrationSourceRepository
from src.core.modules.maintenance.application.common.support import (
    normalize_maintenance_code,
    normalize_optional_text,
)
from src.core.modules.maintenance.application.common.scope_authorization import (
    deny_maintenance_scope_access,
)
from src.core.shared.activity.activity_recorder import record_activity
from src.core.platform.auth.authorization import require_permission
from src.core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.contract.master_data.org.contracts import OrganizationRepository
from src.core.platform.tenancy.tenant_context import (
    TenantContextService,
    require_tenant_context_service,
)
from src.core.shared.events.domain_events import DomainChangeEvent, domain_events
from src.core.platform.domain.master_data.org import Organization


class MaintenanceIntegrationSourceService:
    def __init__(
        self,
        session: Session,
        integration_source_repo: MaintenanceIntegrationSourceRepository,
        *,
        organization_repo: OrganizationRepository,
        sensor_exception_service=None,
        tenant_context_service: TenantContextService | None = None,
        user_session=None,
        activity_service=None,
    ) -> None:
        self._session = session
        self._integration_source_repo = integration_source_repo
        self._organization_repo = organization_repo
        self._tenant_context_service = require_tenant_context_service(
            tenant_context_service,
            consumer_label="MaintenanceIntegrationSourceService",
        )
        self._sensor_exception_service = sensor_exception_service
        self._user_session = user_session
        self._activity_service = activity_service

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
        source = MaintenanceIntegrationSource.create(
            organization_id=organization.id,
            integration_code=integration_code,
            name=name,
            integration_type=integration_type,
            endpoint_or_path=endpoint_or_path,
            authentication_mode=authentication_mode,
            schedule_expression=schedule_expression,
            is_active=bool(is_active),
            notes=notes,
        )
        if self._integration_source_repo.get_by_code(organization.id, source.integration_code) is not None:
            raise ValidationError(
                "Integration code already exists in the active organization.",
                code="MAINTENANCE_INTEGRATION_SOURCE_CODE_EXISTS",
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
        updated = replace(
            source,
            integration_code=source.integration_code if integration_code is None else integration_code,
            name=source.name if name is None else name,
            integration_type=source.integration_type if integration_type is None else integration_type,
            endpoint_or_path=source.endpoint_or_path if endpoint_or_path is None else endpoint_or_path,
            authentication_mode=source.authentication_mode if authentication_mode is None else authentication_mode,
            schedule_expression=source.schedule_expression if schedule_expression is None else schedule_expression,
            last_successful_sync_at=(
                source.last_successful_sync_at
                if last_successful_sync_at is None
                else last_successful_sync_at
            ),
            last_failed_sync_at=(
                source.last_failed_sync_at
                if last_failed_sync_at is None
                else last_failed_sync_at
            ),
            last_error_message=source.last_error_message if last_error_message is None else last_error_message,
            is_active=source.is_active if is_active is None else bool(is_active),
            notes=source.notes if notes is None else notes,
            updated_at=datetime.now(timezone.utc),
        )
        existing = self._integration_source_repo.get_by_code(organization.id, updated.integration_code)
        if existing is not None and existing.id != source.id:
            raise ValidationError(
                "Integration code already exists in the active organization.",
                code="MAINTENANCE_INTEGRATION_SOURCE_CODE_EXISTS",
            )
        try:
            self._integration_source_repo.update(updated)
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
        self._record_change("maintenance_integration_source.update", updated)
        return updated

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
        record_activity(
            self,
            action=action,
            entity_type="maintenance_integration_source",
            entity_id=source.id,
            module="maintenance",
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
            deny_maintenance_scope_access(
                self._user_session,
                operation_label=operation_label,
                message=(
                    f"Permission denied for {operation_label}. Shared "
                    "integration sources require organization-wide maintenance "
                    "access."
                ),
            )

    def _active_organization(self) -> Organization:
        return self._tenant_context_service.require_context(
            operation_label="maintenance integration sources"
        ).organization

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.read", operation_label=operation_label)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.manage", operation_label=operation_label)


__all__ = ["MaintenanceIntegrationSourceService"]
