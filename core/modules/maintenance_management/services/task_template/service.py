from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.modules.maintenance_management.domain import MaintenanceTaskTemplate
from core.modules.maintenance_management.interfaces import MaintenanceTaskTemplateRepository
from core.modules.maintenance_management.support import (
    coerce_optional_non_negative_int,
    coerce_template_status,
    normalize_maintenance_code,
    normalize_maintenance_name,
    normalize_optional_text,
)
from core.platform.audit.helpers import record_audit
from src.core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.org.contracts import OrganizationRepository
from src.core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from src.core.platform.org.domain import Organization


class MaintenanceTaskTemplateService:
    def __init__(
        self,
        session: Session,
        task_template_repo: MaintenanceTaskTemplateRepository,
        *,
        organization_repo: OrganizationRepository,
        user_session=None,
        audit_service=None,
    ) -> None:
        self._session = session
        self._task_template_repo = task_template_repo
        self._organization_repo = organization_repo
        self._user_session = user_session
        self._audit_service = audit_service

    def list_task_templates(
        self,
        *,
        active_only: bool | None = None,
        maintenance_type: str | None = None,
        template_status: str | None = None,
    ) -> list[MaintenanceTaskTemplate]:
        self._require_read("list maintenance task templates")
        self._ensure_org_wide_access("list maintenance task templates")
        organization = self._active_organization()
        return self._task_template_repo.list_for_organization(
            organization.id,
            active_only=active_only,
            maintenance_type=normalize_optional_text(maintenance_type).upper() or None,
            template_status=coerce_template_status(template_status) if template_status not in (None, "") else None,
        )

    def search_task_templates(
        self,
        *,
        search_text: str = "",
        active_only: bool | None = None,
        maintenance_type: str | None = None,
        template_status: str | None = None,
    ) -> list[MaintenanceTaskTemplate]:
        normalized_search = normalize_optional_text(search_text).lower()
        rows = self.list_task_templates(
            active_only=active_only,
            maintenance_type=maintenance_type,
            template_status=template_status,
        )
        if not normalized_search:
            return rows
        return [
            row
            for row in rows
            if normalized_search in " ".join(
                filter(
                    None,
                    [
                        row.task_template_code,
                        row.name,
                        row.description,
                        row.maintenance_type,
                        row.required_skill,
                        row.template_status.value,
                    ],
                )
            ).lower()
        ]

    def get_task_template(self, task_template_id: str) -> MaintenanceTaskTemplate:
        self._require_read("view maintenance task template")
        self._ensure_org_wide_access("view maintenance task template")
        return self._get_task_template(task_template_id, organization=self._active_organization())

    def find_task_template_by_code(
        self,
        task_template_code: str,
        *,
        active_only: bool | None = None,
    ) -> MaintenanceTaskTemplate | None:
        self._require_read("resolve maintenance task template")
        self._ensure_org_wide_access("resolve maintenance task template")
        organization = self._active_organization()
        row = self._task_template_repo.get_by_code(
            organization.id,
            normalize_maintenance_code(task_template_code, label="Task template code"),
        )
        if row is None:
            return None
        if active_only is not None and row.is_active != bool(active_only):
            return None
        return row

    def create_task_template(
        self,
        *,
        task_template_code: str,
        name: str,
        description: str = "",
        maintenance_type: str = "",
        revision_no: int | str = 1,
        template_status=None,
        estimated_minutes: int | str | None = None,
        required_skill: str = "",
        requires_shutdown: bool = False,
        requires_permit: bool = False,
        is_active: bool = True,
        notes: str = "",
    ) -> MaintenanceTaskTemplate:
        self._require_manage("create maintenance task template")
        self._ensure_org_wide_access("create maintenance task template")
        organization = self._active_organization()
        normalized_code = normalize_maintenance_code(task_template_code, label="Task template code")
        if self._task_template_repo.get_by_code(organization.id, normalized_code) is not None:
            raise ValidationError(
                "Task template code already exists in the active organization.",
                code="MAINTENANCE_TASK_TEMPLATE_CODE_EXISTS",
            )
        row = MaintenanceTaskTemplate.create(
            organization_id=organization.id,
            task_template_code=normalized_code,
            name=normalize_maintenance_name(name, label="Task template name"),
            description=normalize_optional_text(description),
            maintenance_type=normalize_optional_text(maintenance_type).upper(),
            revision_no=self._coerce_positive_int(revision_no, label="Revision number"),
            template_status=coerce_template_status(template_status),
            estimated_minutes=coerce_optional_non_negative_int(estimated_minutes, label="Estimated minutes"),
            required_skill=normalize_optional_text(required_skill),
            requires_shutdown=bool(requires_shutdown),
            requires_permit=bool(requires_permit),
            is_active=bool(is_active),
            notes=normalize_optional_text(notes),
        )
        try:
            self._task_template_repo.add(row)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Task template code already exists in the active organization.",
                code="MAINTENANCE_TASK_TEMPLATE_CODE_EXISTS",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_task_template.create", row)
        return row

    def update_task_template(
        self,
        task_template_id: str,
        *,
        task_template_code: str | None = None,
        name: str | None = None,
        description: str | None = None,
        maintenance_type: str | None = None,
        revision_no: int | str | None = None,
        template_status=None,
        estimated_minutes: int | str | None = None,
        required_skill: str | None = None,
        requires_shutdown: bool | None = None,
        requires_permit: bool | None = None,
        is_active: bool | None = None,
        notes: str | None = None,
        expected_version: int | None = None,
    ) -> MaintenanceTaskTemplate:
        self._require_manage("update maintenance task template")
        self._ensure_org_wide_access("update maintenance task template")
        organization = self._active_organization()
        row = self._get_task_template(task_template_id, organization=organization)
        if expected_version is not None and row.version != expected_version:
            raise ConcurrencyError(
                "Maintenance task template changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        if task_template_code is not None:
            normalized_code = normalize_maintenance_code(task_template_code, label="Task template code")
            existing = self._task_template_repo.get_by_code(organization.id, normalized_code)
            if existing is not None and existing.id != row.id:
                raise ValidationError(
                    "Task template code already exists in the active organization.",
                    code="MAINTENANCE_TASK_TEMPLATE_CODE_EXISTS",
                )
            row.task_template_code = normalized_code
        if name is not None:
            row.name = normalize_maintenance_name(name, label="Task template name")
        if description is not None:
            row.description = normalize_optional_text(description)
        if maintenance_type is not None:
            row.maintenance_type = normalize_optional_text(maintenance_type).upper()
        if revision_no is not None:
            row.revision_no = self._coerce_positive_int(revision_no, label="Revision number")
        if template_status is not None:
            row.template_status = coerce_template_status(template_status)
        if estimated_minutes is not None:
            row.estimated_minutes = coerce_optional_non_negative_int(estimated_minutes, label="Estimated minutes")
        if required_skill is not None:
            row.required_skill = normalize_optional_text(required_skill)
        if requires_shutdown is not None:
            row.requires_shutdown = bool(requires_shutdown)
        if requires_permit is not None:
            row.requires_permit = bool(requires_permit)
        if is_active is not None:
            row.is_active = bool(is_active)
        if notes is not None:
            row.notes = normalize_optional_text(notes)
        row.updated_at = datetime.now(timezone.utc)
        try:
            self._task_template_repo.update(row)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Task template code already exists in the active organization.",
                code="MAINTENANCE_TASK_TEMPLATE_CODE_EXISTS",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_task_template.update", row)
        return row

    def _active_organization(self) -> Organization:
        organization = self._organization_repo.get_active()
        if organization is None:
            raise NotFoundError("Active organization not found.", code="ORGANIZATION_NOT_FOUND")
        return organization

    def _get_task_template(
        self,
        task_template_id: str,
        *,
        organization: Organization,
    ) -> MaintenanceTaskTemplate:
        row = self._task_template_repo.get(task_template_id)
        if row is None or row.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance task template not found in the active organization.",
                code="MAINTENANCE_TASK_TEMPLATE_NOT_FOUND",
            )
        return row

    def _ensure_org_wide_access(self, operation_label: str) -> None:
        if self._user_session is not None and self._user_session.is_scope_restricted("maintenance"):
            raise BusinessRuleError(
                f"Permission denied for {operation_label}. Template libraries require broader maintenance access.",
                code="PERMISSION_DENIED",
            )

    def _coerce_positive_int(self, value: int | str, *, label: str) -> int:
        try:
            resolved = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"{label} is invalid.", code=f"{label.upper().replace(' ', '_')}_INVALID") from exc
        if resolved <= 0:
            raise ValidationError(
                f"{label} must be greater than zero.",
                code=f"{label.upper().replace(' ', '_')}_INVALID",
            )
        return resolved

    def _record_change(self, action: str, row: MaintenanceTaskTemplate) -> None:
        record_audit(
            self,
            action=action,
            entity_type="maintenance_task_template",
            entity_id=row.id,
            details={
                "organization_id": row.organization_id,
                "task_template_code": row.task_template_code,
                "name": row.name,
                "revision_no": row.revision_no,
                "template_status": row.template_status.value,
                "maintenance_type": row.maintenance_type,
                "required_skill": row.required_skill,
                "requires_shutdown": row.requires_shutdown,
                "requires_permit": row.requires_permit,
                "is_active": row.is_active,
            },
        )
        domain_events.domain_changed.emit(
            DomainChangeEvent(
                category="module",
                scope_code="maintenance_management",
                entity_type="maintenance_task_template",
                entity_id=row.id,
                source_event="maintenance_task_templates_changed",
            )
        )

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.read", operation_label=operation_label)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.manage", operation_label=operation_label)


__all__ = ["MaintenanceTaskTemplateService"]
