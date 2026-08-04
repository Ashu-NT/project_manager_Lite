from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.maintenance.domain import MaintenanceTaskStepTemplate, MaintenanceTaskTemplate
from src.core.modules.maintenance.contracts.repositories import (
    MaintenanceTaskStepTemplateRepository,
    MaintenanceTaskTemplateRepository,
)
from src.core.modules.maintenance.application.common.support import normalize_optional_text
from src.core.modules.maintenance.application.common.scope_authorization import (
    deny_maintenance_scope_access,
)
from src.core.shared.activity.activity_recorder import record_activity
from src.core.platform.auth.authorization import require_permission
from src.core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.contract.master_data.org.contracts import OrganizationRepository
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
    require_tenant_context_service,
)
from src.core.shared.events.domain_events import DomainChangeEvent, domain_events
from src.core.platform.domain.master_data.org import Organization


class MaintenanceTaskStepTemplateService:
    def __init__(
        self,
        session: Session,
        task_step_template_repo: MaintenanceTaskStepTemplateRepository,
        *,
        organization_repo: OrganizationRepository,
        task_template_repo: MaintenanceTaskTemplateRepository,
        tenant_context_service: TenantContextService | None = None,
        user_session=None,
        activity_service=None,
    ) -> None:
        self._session = session
        self._task_step_template_repo = task_step_template_repo
        self._organization_repo = organization_repo
        self._tenant_context_service = require_tenant_context_service(
            tenant_context_service,
            consumer_label="MaintenanceTaskStepTemplateService",
        )
        self._task_template_repo = task_template_repo
        self._user_session = user_session
        self._activity_service = activity_service

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
        row = MaintenanceTaskStepTemplate.create(
            organization_id=organization.id,
            task_template_id=task_template.id,
            step_number=step_number,
            instruction=instruction,
            expected_result=expected_result,
            hint_level=hint_level,
            hint_text=hint_text,
            requires_confirmation=bool(requires_confirmation),
            requires_measurement=bool(requires_measurement),
            requires_photo=bool(requires_photo),
            measurement_unit=measurement_unit,
            sort_order=step_number if sort_order in (None, "") else sort_order,
            is_active=bool(is_active),
            notes=notes,
        )
        self._ensure_unique_step_number(
            organization.id,
            task_template_id=task_template.id,
            step_number=row.step_number,
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
        updated = replace(
            row,
            step_number=row.step_number if step_number is None else step_number,
            instruction=row.instruction if instruction is None else instruction,
            expected_result=row.expected_result if expected_result is None else expected_result,
            hint_level=row.hint_level if hint_level is None else hint_level,
            hint_text=row.hint_text if hint_text is None else hint_text,
            requires_confirmation=(
                row.requires_confirmation
                if requires_confirmation is None
                else bool(requires_confirmation)
            ),
            requires_measurement=(
                row.requires_measurement
                if requires_measurement is None
                else bool(requires_measurement)
            ),
            requires_photo=row.requires_photo if requires_photo is None else bool(requires_photo),
            measurement_unit=row.measurement_unit if measurement_unit is None else measurement_unit,
            sort_order=row.sort_order if sort_order is None else sort_order,
            is_active=row.is_active if is_active is None else bool(is_active),
            notes=row.notes if notes is None else notes,
            updated_at=datetime.now(timezone.utc),
        )
        self._ensure_unique_step_number(
            organization.id,
            task_template_id=updated.task_template_id,
            step_number=updated.step_number,
            exclude_id=row.id,
        )
        try:
            self._task_step_template_repo.update(updated)
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
        self._record_change("maintenance_task_step_template.update", updated)
        return updated

    def _active_organization(self) -> Organization:
        return self._tenant_context_service.require_context(
            operation_label="maintenance task step templates"
        ).organization

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
            deny_maintenance_scope_access(
                self._user_session,
                operation_label=operation_label,
                message=(
                    f"Permission denied for {operation_label}. Template "
                    "libraries require broader maintenance access."
                ),
            )

    def _record_change(self, action: str, row: MaintenanceTaskStepTemplate) -> None:
        record_activity(
            self,
            action=action,
            entity_type="maintenance_task_step_template",
            entity_id=row.id,
            module="maintenance",
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
