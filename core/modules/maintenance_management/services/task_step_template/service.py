from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.modules.maintenance_management.domain import MaintenanceTaskStepTemplate, MaintenanceTaskTemplate
from core.modules.maintenance_management.interfaces import (
    MaintenanceTaskStepTemplateRepository,
    MaintenanceTaskTemplateRepository,
)
from core.modules.maintenance_management.support import (
    coerce_optional_non_negative_int,
    normalize_maintenance_name,
    normalize_optional_text,
)
from core.platform.audit.helpers import record_audit
from src.core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.org.contracts import OrganizationRepository
from core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from src.core.platform.org.domain import Organization


class MaintenanceTaskStepTemplateService:
    def __init__(
        self,
        session: Session,
        task_step_template_repo: MaintenanceTaskStepTemplateRepository,
        *,
        organization_repo: OrganizationRepository,
        task_template_repo: MaintenanceTaskTemplateRepository,
        user_session=None,
        audit_service=None,
    ) -> None:
        self._session = session
        self._task_step_template_repo = task_step_template_repo
        self._organization_repo = organization_repo
        self._task_template_repo = task_template_repo
        self._user_session = user_session
        self._audit_service = audit_service

    def list_step_templates(
        self,
        *,
        task_template_id: str | None = None,
        active_only: bool | None = None,
    ) -> list[MaintenanceTaskStepTemplate]:
        self._require_read("list maintenance task step templates")
        self._ensure_org_wide_access("list maintenance task step templates")
        organization = self._active_organization()
        if task_template_id is not None:
            self._get_task_template(task_template_id, organization=organization)
        return self._task_step_template_repo.list_for_organization(
            organization.id,
            task_template_id=normalize_optional_text(task_template_id) or None,
            active_only=active_only,
        )

    def get_step_template(self, task_step_template_id: str) -> MaintenanceTaskStepTemplate:
        self._require_read("view maintenance task step template")
        self._ensure_org_wide_access("view maintenance task step template")
        return self._get_step_template(task_step_template_id, organization=self._active_organization())

    def create_step_template(
        self,
        *,
        task_template_id: str,
        step_number: int | str,
        instruction: str,
        expected_result: str = "",
        hint_level: str = "",
        hint_text: str = "",
        requires_confirmation: bool = False,
        requires_measurement: bool = False,
        requires_photo: bool = False,
        measurement_unit: str = "",
        sort_order: int | str | None = None,
        is_active: bool = True,
        notes: str = "",
    ) -> MaintenanceTaskStepTemplate:
        self._require_manage("create maintenance task step template")
        self._ensure_org_wide_access("create maintenance task step template")
        organization = self._active_organization()
        task_template = self._get_task_template(task_template_id, organization=organization)
        resolved_step_number = self._coerce_positive_int(step_number, label="Step number")
        self._ensure_unique_step_number(
            organization.id,
            task_template_id=task_template.id,
            step_number=resolved_step_number,
        )
        resolved_sort_order = (
            resolved_step_number
            if sort_order in (None, "")
            else self._coerce_positive_int(sort_order, label="Sort order")
        )
        row = MaintenanceTaskStepTemplate.create(
            organization_id=organization.id,
            task_template_id=task_template.id,
            step_number=resolved_step_number,
            instruction=normalize_maintenance_name(instruction, label="Instruction"),
            expected_result=normalize_optional_text(expected_result),
            hint_level=normalize_optional_text(hint_level).upper(),
            hint_text=normalize_optional_text(hint_text),
            requires_confirmation=bool(requires_confirmation),
            requires_measurement=bool(requires_measurement),
            requires_photo=bool(requires_photo),
            measurement_unit=normalize_optional_text(measurement_unit).upper(),
            sort_order=resolved_sort_order,
            is_active=bool(is_active),
            notes=normalize_optional_text(notes),
        )
        try:
            self._task_step_template_repo.add(row)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Task step template could not be saved.",
                code="MAINTENANCE_TASK_STEP_TEMPLATE_SAVE_FAILED",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_task_step_template.create", row)
        return row

    def update_step_template(
        self,
        task_step_template_id: str,
        *,
        step_number: int | str | None = None,
        instruction: str | None = None,
        expected_result: str | None = None,
        hint_level: str | None = None,
        hint_text: str | None = None,
        requires_confirmation: bool | None = None,
        requires_measurement: bool | None = None,
        requires_photo: bool | None = None,
        measurement_unit: str | None = None,
        sort_order: int | str | None = None,
        is_active: bool | None = None,
        notes: str | None = None,
        expected_version: int | None = None,
    ) -> MaintenanceTaskStepTemplate:
        self._require_manage("update maintenance task step template")
        self._ensure_org_wide_access("update maintenance task step template")
        organization = self._active_organization()
        row = self._get_step_template(task_step_template_id, organization=organization)
        if expected_version is not None and row.version != expected_version:
            raise ConcurrencyError(
                "Maintenance task step template changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        if step_number is not None:
            resolved_step_number = self._coerce_positive_int(step_number, label="Step number")
            self._ensure_unique_step_number(
                organization.id,
                task_template_id=row.task_template_id,
                step_number=resolved_step_number,
                exclude_id=row.id,
            )
            row.step_number = resolved_step_number
        if instruction is not None:
            row.instruction = normalize_maintenance_name(instruction, label="Instruction")
        if expected_result is not None:
            row.expected_result = normalize_optional_text(expected_result)
        if hint_level is not None:
            row.hint_level = normalize_optional_text(hint_level).upper()
        if hint_text is not None:
            row.hint_text = normalize_optional_text(hint_text)
        if requires_confirmation is not None:
            row.requires_confirmation = bool(requires_confirmation)
        if requires_measurement is not None:
            row.requires_measurement = bool(requires_measurement)
        if requires_photo is not None:
            row.requires_photo = bool(requires_photo)
        if measurement_unit is not None:
            row.measurement_unit = normalize_optional_text(measurement_unit).upper()
        if sort_order is not None:
            row.sort_order = self._coerce_positive_int(sort_order, label="Sort order")
        if is_active is not None:
            row.is_active = bool(is_active)
        if notes is not None:
            row.notes = normalize_optional_text(notes)
        row.updated_at = datetime.now(timezone.utc)
        try:
            self._task_step_template_repo.update(row)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Task step template could not be updated.",
                code="MAINTENANCE_TASK_STEP_TEMPLATE_SAVE_FAILED",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_task_step_template.update", row)
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

    def _get_step_template(
        self,
        task_step_template_id: str,
        *,
        organization: Organization,
    ) -> MaintenanceTaskStepTemplate:
        row = self._task_step_template_repo.get(task_step_template_id)
        if row is None or row.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance task step template not found in the active organization.",
                code="MAINTENANCE_TASK_STEP_TEMPLATE_NOT_FOUND",
            )
        return row

    def _ensure_unique_step_number(
        self,
        organization_id: str,
        *,
        task_template_id: str,
        step_number: int,
        exclude_id: str | None = None,
    ) -> None:
        rows = self._task_step_template_repo.list_for_organization(
            organization_id,
            task_template_id=task_template_id,
            active_only=None,
        )
        if any(row.step_number == step_number and row.id != exclude_id for row in rows):
            raise ValidationError(
                "Step number already exists on the selected task template.",
                code="MAINTENANCE_TASK_STEP_TEMPLATE_STEP_EXISTS",
            )

    def _ensure_org_wide_access(self, operation_label: str) -> None:
        if self._user_session is not None and self._user_session.is_scope_restricted("maintenance"):
            raise BusinessRuleError(
                f"Permission denied for {operation_label}. Template libraries require broader maintenance access.",
                code="PERMISSION_DENIED",
            )

    def _coerce_positive_int(self, value: int | str, *, label: str) -> int:
        resolved = coerce_optional_non_negative_int(value, label=label)
        if resolved is None or resolved <= 0:
            raise ValidationError(
                f"{label} must be greater than zero.",
                code=f"{label.upper().replace(' ', '_')}_INVALID",
            )
        return resolved

    def _record_change(self, action: str, row: MaintenanceTaskStepTemplate) -> None:
        record_audit(
            self,
            action=action,
            entity_type="maintenance_task_step_template",
            entity_id=row.id,
            details={
                "organization_id": row.organization_id,
                "task_template_id": row.task_template_id,
                "step_number": row.step_number,
                "instruction": row.instruction,
                "sort_order": row.sort_order,
                "requires_confirmation": row.requires_confirmation,
                "requires_measurement": row.requires_measurement,
                "requires_photo": row.requires_photo,
                "is_active": row.is_active,
            },
        )
        domain_events.domain_changed.emit(
            DomainChangeEvent(
                category="module",
                scope_code="maintenance_management",
                entity_type="maintenance_task_step_template",
                entity_id=row.id,
                source_event="maintenance_task_step_templates_changed",
            )
        )

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.read", operation_label=operation_label)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.manage", operation_label=operation_label)


__all__ = ["MaintenanceTaskStepTemplateService"]
