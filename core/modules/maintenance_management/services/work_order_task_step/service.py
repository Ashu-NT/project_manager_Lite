from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.modules.maintenance_management.domain import (
    MaintenanceTaskCompletionRule,
    MaintenanceWorkOrderStatus,
    MaintenanceWorkOrderTask,
    MaintenanceWorkOrderTaskStatus,
    MaintenanceWorkOrderTaskStep,
    MaintenanceWorkOrderTaskStepStatus,
)
from core.modules.maintenance_management.interfaces import (
    MaintenanceWorkOrderRepository,
    MaintenanceWorkOrderTaskRepository,
    MaintenanceWorkOrderTaskStepRepository,
)
from core.modules.maintenance_management.services.work_order_task_step.validation import (
    MaintenanceWorkOrderTaskStepValidationMixin,
)
from core.modules.maintenance_management.support import (
    coerce_work_order_task_step_status,
    normalize_maintenance_name,
    normalize_optional_text,
)
from core.platform.access.authorization import filter_scope_rows, require_scope_permission
from core.platform.audit.helpers import record_audit
from src.core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from core.platform.common.interfaces import OrganizationRepository
from core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from core.platform.org.domain import Organization


class MaintenanceWorkOrderTaskStepService(MaintenanceWorkOrderTaskStepValidationMixin):
    def __init__(
        self,
        session: Session,
        work_order_task_step_repo: MaintenanceWorkOrderTaskStepRepository,
        *,
        organization_repo: OrganizationRepository,
        work_order_repo: MaintenanceWorkOrderRepository,
        work_order_task_repo: MaintenanceWorkOrderTaskRepository,
        user_session=None,
        audit_service=None,
    ) -> None:
        self._session = session
        self._work_order_task_step_repo = work_order_task_step_repo
        self._organization_repo = organization_repo
        self._work_order_repo = work_order_repo
        self._work_order_task_repo = work_order_task_repo
        self._user_session = user_session
        self._audit_service = audit_service

    def list_steps(
        self,
        *,
        work_order_task_id: str | None = None,
        status: str | None = None,
    ) -> list[MaintenanceWorkOrderTaskStep]:
        self._require_read("list maintenance work order task steps")
        organization = self._active_organization()
        if work_order_task_id is not None:
            self._get_task(work_order_task_id, organization=organization)
        rows = self._work_order_task_step_repo.list_for_organization(
            organization.id,
            work_order_task_id=work_order_task_id,
            status=status,
        )
        return filter_scope_rows(
            rows,
            self._user_session,
            scope_type="maintenance",
            permission_code="maintenance.read",
            scope_id_getter=self._scope_anchor_for,
        )

    def get_step(self, work_order_task_step_id: str) -> MaintenanceWorkOrderTaskStep:
        self._require_read("view maintenance work order task step")
        organization = self._active_organization()
        step = self._work_order_task_step_repo.get(work_order_task_step_id)
        if step is None or step.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance work order task step not found in the active organization.",
                code="MAINTENANCE_WORK_ORDER_TASK_STEP_NOT_FOUND",
            )
        self._require_scope_read(self._scope_anchor_for(step), operation_label="view maintenance work order task step")
        return step

    def create_step(
        self,
        *,
        work_order_task_id: str,
        instruction: str,
        source_step_template_id: str | None = None,
        step_number: int | str | None = None,
        expected_result: str = "",
        hint_level: str = "",
        hint_text: str = "",
        requires_confirmation: bool = False,
        requires_measurement: bool = False,
        requires_photo: bool = False,
        measurement_unit: str = "",
        notes: str = "",
    ) -> MaintenanceWorkOrderTaskStep:
        self._require_manage("create maintenance work order task step")
        organization = self._active_organization()
        task = self._get_task(work_order_task_id, organization=organization)
        work_order = self._get_work_order(task.work_order_id, organization=organization)
        self._ensure_work_order_is_mutable(work_order)

        resolved_step_number = self._resolve_step_number(task.id, step_number)
        if any(row.step_number == resolved_step_number for row in self._work_order_task_step_repo.list_for_organization(organization.id, work_order_task_id=task.id)):
            raise ValidationError(
                "Step number already exists on the selected work order task.",
                code="MAINTENANCE_WORK_ORDER_TASK_STEP_NUMBER_EXISTS",
            )

        step = MaintenanceWorkOrderTaskStep.create(
            organization_id=organization.id,
            work_order_task_id=task.id,
            source_step_template_id=(str(source_step_template_id or "").strip() or None),
            step_number=resolved_step_number,
            instruction=normalize_maintenance_name(instruction, label="Instruction"),
            expected_result=normalize_optional_text(expected_result),
            hint_level=normalize_optional_text(hint_level).upper(),
            hint_text=normalize_optional_text(hint_text),
            requires_confirmation=bool(requires_confirmation),
            requires_measurement=bool(requires_measurement),
            requires_photo=bool(requires_photo),
            measurement_unit=normalize_optional_text(measurement_unit),
            notes=normalize_optional_text(notes),
        )
        try:
            self._work_order_task_step_repo.add(step)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Maintenance work order task step could not be saved.",
                code="MAINTENANCE_WORK_ORDER_TASK_STEP_SAVE_FAILED",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_work_order_task_step.create", step)
        return step

    def update_step(
        self,
        work_order_task_step_id: str,
        *,
        instruction: str | None = None,
        source_step_template_id: str | None = None,
        step_number: int | str | None = None,
        expected_result: str | None = None,
        hint_level: str | None = None,
        hint_text: str | None = None,
        status: str | None = None,
        requires_confirmation: bool | None = None,
        requires_measurement: bool | None = None,
        requires_photo: bool | None = None,
        measurement_value: str | None = None,
        measurement_unit: str | None = None,
        confirm_completion: bool | None = None,
        notes: str | None = None,
        expected_version: int | None = None,
    ) -> MaintenanceWorkOrderTaskStep:
        self._require_manage("update maintenance work order task step")
        step = self.get_step(work_order_task_step_id)
        task = self._get_task(step.work_order_task_id, organization=self._active_organization())
        work_order = self._get_work_order(task.work_order_id, organization=self._active_organization())
        self._ensure_work_order_is_mutable(work_order)

        if expected_version is not None and step.version != expected_version:
            raise ConcurrencyError(
                "Maintenance work order task step changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )

        if instruction is not None:
            step.instruction = normalize_maintenance_name(instruction, label="Instruction")
        if source_step_template_id is not None:
            step.source_step_template_id = (str(source_step_template_id or "").strip() or None)
        if expected_result is not None:
            step.expected_result = normalize_optional_text(expected_result)
        if hint_level is not None:
            step.hint_level = normalize_optional_text(hint_level).upper()
        if hint_text is not None:
            step.hint_text = normalize_optional_text(hint_text)
        if requires_confirmation is not None:
            step.requires_confirmation = bool(requires_confirmation)
        if requires_measurement is not None:
            step.requires_measurement = bool(requires_measurement)
        if requires_photo is not None:
            step.requires_photo = bool(requires_photo)
        if measurement_value is not None:
            step.measurement_value = normalize_optional_text(measurement_value)
        if measurement_unit is not None:
            step.measurement_unit = normalize_optional_text(measurement_unit)
        if notes is not None:
            step.notes = normalize_optional_text(notes)

        if step_number is not None:
            resolved_step_number = self._resolve_step_number(task.id, step_number)
            sibling_rows = self._work_order_task_step_repo.list_for_organization(
                task.organization_id,
                work_order_task_id=task.id,
            )
            if any(row.step_number == resolved_step_number and row.id != step.id for row in sibling_rows):
                raise ValidationError(
                    "Step number already exists on the selected work order task.",
                    code="MAINTENANCE_WORK_ORDER_TASK_STEP_NUMBER_EXISTS",
                )
            step.step_number = resolved_step_number

        if status is not None:
            new_status = coerce_work_order_task_step_status(status)
            self._validate_work_order_task_step_status_transition(step.status, new_status)
            if step.requires_measurement and new_status == MaintenanceWorkOrderTaskStepStatus.DONE and not normalize_optional_text(step.measurement_value):
                raise ValidationError(
                    "Measurement value is required before completing this step.",
                    code="MAINTENANCE_WORK_ORDER_TASK_STEP_MEASUREMENT_REQUIRED",
                )
            step.status = new_status
            now = datetime.now(timezone.utc)
            current_user_id = self._current_user_id()
            if new_status == MaintenanceWorkOrderTaskStepStatus.IN_PROGRESS and task.status == MaintenanceWorkOrderTaskStatus.NOT_STARTED:
                task.status = MaintenanceWorkOrderTaskStatus.IN_PROGRESS
                if task.started_at is None:
                    task.started_at = now
                task.updated_at = now
                self._work_order_task_repo.update(task)
            if new_status in {
                MaintenanceWorkOrderTaskStepStatus.DONE,
                MaintenanceWorkOrderTaskStepStatus.SKIPPED,
            }:
                if step.completed_at is None:
                    step.completed_at = now
                if current_user_id:
                    step.completed_by_user_id = current_user_id
            if new_status == MaintenanceWorkOrderTaskStepStatus.FAILED:
                step.confirmed_at = None
                step.confirmed_by_user_id = None

        if confirm_completion is not None:
            if confirm_completion:
                if not step.requires_confirmation:
                    raise ValidationError(
                        "This step does not require confirmation.",
                        code="MAINTENANCE_WORK_ORDER_TASK_STEP_CONFIRMATION_NOT_REQUIRED",
                    )
                if step.status != MaintenanceWorkOrderTaskStepStatus.DONE:
                    raise ValidationError(
                        "Only completed steps can be confirmed.",
                        code="MAINTENANCE_WORK_ORDER_TASK_STEP_CONFIRMATION_INVALID",
                    )
                step.confirmed_at = datetime.now(timezone.utc)
                step.confirmed_by_user_id = self._current_user_id()
            else:
                step.confirmed_at = None
                step.confirmed_by_user_id = None

        step.updated_at = datetime.now(timezone.utc)

        try:
            self._work_order_task_step_repo.update(step)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Maintenance work order task step could not be updated.",
                code="MAINTENANCE_WORK_ORDER_TASK_STEP_SAVE_FAILED",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_work_order_task_step.update", step)
        return step

    def _active_organization(self) -> Organization:
        organization = self._organization_repo.get_active()
        if organization is None:
            raise NotFoundError("Active organization not found.", code="ORGANIZATION_NOT_FOUND")
        return organization

    def _get_task(self, work_order_task_id: str, *, organization: Organization) -> MaintenanceWorkOrderTask:
        task = self._work_order_task_repo.get(work_order_task_id)
        if task is None or task.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance work order task not found in the active organization.",
                code="MAINTENANCE_WORK_ORDER_TASK_NOT_FOUND",
            )
        return task

    def _get_work_order(self, work_order_id: str, *, organization: Organization):
        work_order = self._work_order_repo.get(work_order_id)
        if work_order is None or work_order.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance work order not found in the active organization.",
                code="MAINTENANCE_WORK_ORDER_NOT_FOUND",
            )
        return work_order

    def _resolve_step_number(self, work_order_task_id: str, step_number: int | str | None) -> int:
        if step_number not in (None, ""):
            resolved = int(step_number)
            if resolved <= 0:
                raise ValidationError(
                    "Step number must be greater than zero.",
                    code="MAINTENANCE_WORK_ORDER_TASK_STEP_NUMBER_INVALID",
                )
            return resolved
        existing_rows = self._work_order_task_step_repo.list_for_organization(
            self._active_organization().id,
            work_order_task_id=work_order_task_id,
        )
        highest = max((row.step_number for row in existing_rows), default=0)
        return highest + 1

    def _ensure_work_order_is_mutable(self, work_order) -> None:
        if work_order.status in {MaintenanceWorkOrderStatus.CANCELLED, MaintenanceWorkOrderStatus.CLOSED}:
            raise BusinessRuleError(
                "Task steps cannot be changed once the work order is cancelled or closed.",
                code="MAINTENANCE_WORK_ORDER_NOT_MUTABLE",
            )

    def _scope_anchor_for(self, step: MaintenanceWorkOrderTaskStep) -> str:
        task = self._work_order_task_repo.get(step.work_order_task_id)
        if task is None:
            return ""
        work_order = self._work_order_repo.get(task.work_order_id)
        if work_order is None:
            return ""
        if work_order.asset_id:
            return work_order.asset_id
        if work_order.system_id:
            return work_order.system_id
        if work_order.location_id:
            return work_order.location_id
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

    def _current_user_id(self) -> str | None:
        principal = getattr(self._user_session, "principal", None)
        return getattr(principal, "user_id", None) if principal is not None else None

    def _record_change(self, action: str, step: MaintenanceWorkOrderTaskStep) -> None:
        record_audit(
            self,
            action=action,
            entity_type="maintenance_work_order_task_step",
            entity_id=step.id,
            details={
                "organization_id": step.organization_id,
                "work_order_task_id": step.work_order_task_id,
                "step_number": step.step_number,
                "status": step.status.value,
                "requires_confirmation": step.requires_confirmation,
                "requires_measurement": step.requires_measurement,
                "requires_photo": step.requires_photo,
            },
        )
        domain_events.domain_changed.emit(
            DomainChangeEvent(
                category="module",
                scope_code="maintenance_management",
                entity_type="maintenance_work_order_task_step",
                entity_id=step.id,
                source_event="maintenance_work_order_task_steps_changed",
            )
        )

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.read", operation_label=operation_label)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.manage", operation_label=operation_label)


def task_steps_satisfy_completion_rule(
    task: MaintenanceWorkOrderTask,
    steps: list[MaintenanceWorkOrderTaskStep],
) -> bool:
    if task.completion_rule != MaintenanceTaskCompletionRule.ALL_STEPS_REQUIRED:
        return True
    if not steps:
        return False
    for step in steps:
        if step.status != MaintenanceWorkOrderTaskStepStatus.DONE:
            return False
        if step.requires_confirmation and step.confirmed_at is None:
            return False
        if step.requires_measurement and not normalize_optional_text(step.measurement_value):
            return False
    return True


__all__ = ["MaintenanceWorkOrderTaskStepService", "task_steps_satisfy_completion_rule"]
