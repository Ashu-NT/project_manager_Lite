from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.maintenance.domain import MaintenanceFailureCode, MaintenanceFailureCodeType
from src.core.modules.maintenance.contracts.repositories import MaintenanceFailureCodeRepository
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


class MaintenanceFailureCodeService:
    def __init__(
        self,
        session: Session,
        failure_code_repo: MaintenanceFailureCodeRepository,
        *,
        organization_repo: OrganizationRepository,
        tenant_context_service: TenantContextService | None = None,
        user_session=None,
        activity_service=None,
    ) -> None:
        self._session = session
        self._failure_code_repo = failure_code_repo
        self._organization_repo = organization_repo
        self._tenant_context_service = require_tenant_context_service(
            tenant_context_service,
            consumer_label="MaintenanceFailureCodeService",
        )
        self._user_session = user_session
        self._activity_service = activity_service

    def list_failure_codes(
        self,
        *,
        active_only: bool | None = None,
        code_type: str | None = None,
        parent_code_id: str | None = None,
    ) -> list[MaintenanceFailureCode]:
        self._require_read("list maintenance failure codes")
        self._ensure_org_wide_access("list maintenance failure codes")
        organization = self._active_organization()
        if parent_code_id is not None:
            self._get_failure_code(parent_code_id, organization=organization)
        return self._failure_code_repo.list_for_organization(
            organization.id,
            active_only=active_only,
            code_type=normalize_optional_text(code_type).upper() or None,
            parent_code_id=normalize_optional_text(parent_code_id) or None,
        )

    def search_failure_codes(
        self,
        *,
        search_text: str = "",
        active_only: bool | None = None,
        code_type: str | None = None,
    ) -> list[MaintenanceFailureCode]:
        normalized_search = normalize_optional_text(search_text).lower()
        rows = self.list_failure_codes(active_only=active_only, code_type=code_type)
        if not normalized_search:
            return rows
        return [
            row
            for row in rows
            if normalized_search in " ".join(
                filter(
                    None,
                    [row.failure_code, row.name, row.description, row.code_type.value],
                )
            ).lower()
        ]

    def get_failure_code(self, failure_code_id: str) -> MaintenanceFailureCode:
        self._require_read("view maintenance failure code")
        self._ensure_org_wide_access("view maintenance failure code")
        return self._get_failure_code(failure_code_id, organization=self._active_organization())

    def find_failure_code_by_code(
        self,
        failure_code: str,
        *,
        active_only: bool | None = None,
    ) -> MaintenanceFailureCode | None:
        self._require_read("resolve maintenance failure code")
        self._ensure_org_wide_access("resolve maintenance failure code")
        organization = self._active_organization()
        row = self._failure_code_repo.get_by_code(
            organization.id,
            normalize_maintenance_code(failure_code, label="Failure code"),
        )
        if row is None:
            return None
        if active_only is not None and row.is_active != bool(active_only):
            return None
        return row

    def create_failure_code(
        self,
        *,
        failure_code: str,
        name: str,
        description: str = "",
        code_type=None,
        parent_code_id: str | None = None,
        is_active: bool = True,
    ) -> MaintenanceFailureCode:
        self._require_manage("create maintenance failure code")
        self._ensure_org_wide_access("create maintenance failure code")
        organization = self._active_organization()
        row = MaintenanceFailureCode.create(
            organization_id=organization.id,
            failure_code=failure_code,
            name=name,
            description=description,
            code_type=code_type,
            parent_code_id=parent_code_id,
            is_active=bool(is_active),
        )
        if self._failure_code_repo.get_by_code(organization.id, row.failure_code) is not None:
            raise ValidationError(
                "Failure code already exists in the active organization.",
                code="MAINTENANCE_FAILURE_CODE_EXISTS",
            )
        parent = self._resolve_parent_code(
            row.parent_code_id,
            organization=organization,
            code_type=row.code_type,
        )
        row = replace(row, parent_code_id=parent.id if parent is not None else None)
        try:
            self._failure_code_repo.add(row)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Failure code already exists in the active organization.",
                code="MAINTENANCE_FAILURE_CODE_EXISTS",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_failure_code.create", row)
        return row

    def update_failure_code(
        self,
        failure_code_id: str,
        *,
        failure_code: str | None = None,
        name: str | None = None,
        description: str | None = None,
        code_type=None,
        parent_code_id: str | None = None,
        is_active: bool | None = None,
        expected_version: int | None = None,
    ) -> MaintenanceFailureCode:
        self._require_manage("update maintenance failure code")
        self._ensure_org_wide_access("update maintenance failure code")
        organization = self._active_organization()
        row = self._get_failure_code(failure_code_id, organization=organization)
        if expected_version is not None and row.version != expected_version:
            raise ConcurrencyError(
                "Maintenance failure code changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        updated = replace(
            row,
            failure_code=row.failure_code if failure_code is None else failure_code,
            name=row.name if name is None else name,
            description=row.description if description is None else description,
            code_type=row.code_type if code_type is None else code_type,
            parent_code_id=row.parent_code_id if parent_code_id is None else parent_code_id,
            is_active=row.is_active if is_active is None else bool(is_active),
            updated_at=datetime.now(timezone.utc),
        )
        existing = self._failure_code_repo.get_by_code(organization.id, updated.failure_code)
        if existing is not None and existing.id != row.id:
            raise ValidationError(
                "Failure code already exists in the active organization.",
                code="MAINTENANCE_FAILURE_CODE_EXISTS",
            )
        parent = self._resolve_parent_code(
            updated.parent_code_id,
            organization=organization,
            code_type=updated.code_type,
            self_id=row.id,
        )
        updated = replace(updated, parent_code_id=parent.id if parent is not None else None)
        try:
            self._failure_code_repo.update(updated)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Failure code already exists in the active organization.",
                code="MAINTENANCE_FAILURE_CODE_EXISTS",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_failure_code.update", updated)
        return updated

    def _active_organization(self) -> Organization:
        return self._tenant_context_service.require_context(
            operation_label="maintenance failure codes"
        ).organization

    def _get_failure_code(
        self,
        failure_code_id: str,
        *,
        organization: Organization,
    ) -> MaintenanceFailureCode:
        row = self._failure_code_repo.get(failure_code_id)
        if row is None or row.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance failure code not found in the active organization.",
                code="MAINTENANCE_FAILURE_CODE_NOT_FOUND",
            )
        return row

    def _resolve_parent_code(
        self,
        parent_code_id: str | None,
        *,
        organization: Organization,
        code_type: MaintenanceFailureCodeType,
        self_id: str | None = None,
    ) -> MaintenanceFailureCode | None:
        if not parent_code_id:
            return None
        if self_id is not None and parent_code_id == self_id:
            raise ValidationError(
                "Failure code cannot be its own parent.",
                code="MAINTENANCE_FAILURE_CODE_PARENT_INVALID",
            )
        parent = self._get_failure_code(parent_code_id, organization=organization)
        if parent.code_type != code_type:
            raise ValidationError(
                "Failure code parent must use the same code type.",
                code="MAINTENANCE_FAILURE_CODE_PARENT_TYPE_MISMATCH",
            )
        return parent

    def _ensure_org_wide_access(self, operation_label: str) -> None:
        if self._user_session is not None and self._user_session.is_scope_restricted("maintenance"):
            deny_maintenance_scope_access(
                self._user_session,
                operation_label=operation_label,
                message=(
                    f"Permission denied for {operation_label}. Failure-code "
                    "libraries require broader maintenance access."
                ),
            )

    def _record_change(self, action: str, row: MaintenanceFailureCode) -> None:
        record_activity(
            self,
            action=action,
            entity_type="maintenance_failure_code",
            entity_id=row.id,
            module="maintenance",
            details={
                "organization_id": row.organization_id,
                "failure_code": row.failure_code,
                "name": row.name,
                "code_type": row.code_type.value,
                "parent_code_id": row.parent_code_id,
                "is_active": row.is_active,
            },
        )
        domain_events.domain_changed.emit(
            DomainChangeEvent(
                category="module",
                scope_code="maintenance_management",
                entity_type="maintenance_failure_code",
                entity_id=row.id,
                source_event="maintenance_failure_codes_changed",
            )
        )

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.read", operation_label=operation_label)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.manage", operation_label=operation_label)


__all__ = ["MaintenanceFailureCodeService"]
