from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.modules.maintenance_management.domain import MaintenanceFailureCode, MaintenanceFailureCodeType
from core.modules.maintenance_management.interfaces import MaintenanceFailureCodeRepository
from core.modules.maintenance_management.support import (
    coerce_failure_code_type,
    normalize_maintenance_code,
    normalize_maintenance_name,
    normalize_optional_text,
)
from core.platform.audit.helpers import record_audit
from src.core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.org.contracts import OrganizationRepository
from core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from src.core.platform.org.domain import Organization


class MaintenanceFailureCodeService:
    def __init__(
        self,
        session: Session,
        failure_code_repo: MaintenanceFailureCodeRepository,
        *,
        organization_repo: OrganizationRepository,
        user_session=None,
        audit_service=None,
    ) -> None:
        self._session = session
        self._failure_code_repo = failure_code_repo
        self._organization_repo = organization_repo
        self._user_session = user_session
        self._audit_service = audit_service

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
        normalized_code = normalize_maintenance_code(failure_code, label="Failure code")
        if self._failure_code_repo.get_by_code(organization.id, normalized_code) is not None:
            raise ValidationError(
                "Failure code already exists in the active organization.",
                code="MAINTENANCE_FAILURE_CODE_EXISTS",
            )
        resolved_code_type = coerce_failure_code_type(code_type)
        parent = self._resolve_parent_code(
            normalize_optional_text(parent_code_id) or None,
            organization=organization,
            code_type=resolved_code_type,
        )
        row = MaintenanceFailureCode.create(
            organization_id=organization.id,
            failure_code=normalized_code,
            name=normalize_maintenance_name(name, label="Failure code name"),
            description=normalize_optional_text(description),
            code_type=resolved_code_type,
            parent_code_id=parent.id if parent is not None else None,
            is_active=bool(is_active),
        )
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
        if failure_code is not None:
            normalized_code = normalize_maintenance_code(failure_code, label="Failure code")
            existing = self._failure_code_repo.get_by_code(organization.id, normalized_code)
            if existing is not None and existing.id != row.id:
                raise ValidationError(
                    "Failure code already exists in the active organization.",
                    code="MAINTENANCE_FAILURE_CODE_EXISTS",
                )
            row.failure_code = normalized_code
        if name is not None:
            row.name = normalize_maintenance_name(name, label="Failure code name")
        if description is not None:
            row.description = normalize_optional_text(description)
        if is_active is not None:
            row.is_active = bool(is_active)
        target_code_type = row.code_type if code_type is None else coerce_failure_code_type(code_type)
        requested_parent_id = row.parent_code_id if parent_code_id is None else (normalize_optional_text(parent_code_id) or None)
        parent = self._resolve_parent_code(
            requested_parent_id,
            organization=organization,
            code_type=target_code_type,
            self_id=row.id,
        )
        row.code_type = target_code_type
        row.parent_code_id = parent.id if parent is not None else None
        row.updated_at = datetime.now(timezone.utc)
        try:
            self._failure_code_repo.update(row)
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
        self._record_change("maintenance_failure_code.update", row)
        return row

    def _active_organization(self) -> Organization:
        organization = self._organization_repo.get_active()
        if organization is None:
            raise NotFoundError("Active organization not found.", code="ORGANIZATION_NOT_FOUND")
        return organization

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
            raise BusinessRuleError(
                f"Permission denied for {operation_label}. Failure-code libraries require broader maintenance access.",
                code="PERMISSION_DENIED",
            )

    def _record_change(self, action: str, row: MaintenanceFailureCode) -> None:
        record_audit(
            self,
            action=action,
            entity_type="maintenance_failure_code",
            entity_id=row.id,
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
