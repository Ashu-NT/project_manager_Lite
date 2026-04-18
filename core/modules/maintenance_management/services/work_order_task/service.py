from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.modules.maintenance_management.domain import (
    MaintenanceTaskCompletionRule,
    MaintenanceWorkOrder,
    MaintenanceWorkOrderStatus,
    MaintenanceWorkOrderTask,
    MaintenanceWorkOrderTaskStatus,
)
from core.modules.maintenance_management.interfaces import (
    MaintenanceWorkOrderRepository,
    MaintenanceWorkOrderTaskRepository,
    MaintenanceWorkOrderTaskStepRepository,
)
from core.modules.maintenance_management.services.work_order_task.validation import (
    MaintenanceWorkOrderTaskValidationMixin,
)
from core.modules.maintenance_management.services.work_order_task_step import task_steps_satisfy_completion_rule
from core.modules.maintenance_management.support import (
    coerce_optional_non_negative_int,
    coerce_task_completion_rule,
    coerce_work_order_task_status,
    normalize_maintenance_name,
    normalize_optional_text,
)
from src.core.platform.access.authorization import filter_scope_rows, require_scope_permission
from src.core.platform.audit.helpers import record_audit
from src.core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.org.contracts import OrganizationRepository
from src.core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from src.core.platform.org.domain import Organization


class MaintenanceWorkOrderTaskService(MaintenanceWorkOrderTaskValidationMixin):
    def __init__(
        self,
        session: Session,
        work_order_task_repo: MaintenanceWorkOrderTaskRepository,
        *,
        organization_repo: OrganizationRepository,
        work_order_repo: MaintenanceWorkOrderRepository,
        work_order_task_step_repo: MaintenanceWorkOrderTaskStepRepository | None = None,
        user_session=None,
        audit_service=None,
    ) -> None:
        self._session = session
        self._work_order_task_repo = work_order_task_repo
        self._organization_repo = organization_repo
        self._work_order_repo = work_order_repo
        self._work_order_task_step_repo = work_order_task_step_repo
        self._user_session = user_session
        self._audit_service = audit_service

    def list_tasks(
        self,
        *,
        work_order_id: str | None = None,
        status: str | None = None,
        assigned_employee_id: str | None = None,
        assigned_team_id: str | None = None,
    ) -> list[MaintenanceWorkOrderTask]:
        self._require_read("list maintenance work order tasks")
        organization = self._active_organization()
        if work_order_id is not None:
            self._get_work_order(work_order_id, organization=organization)
        rows = self._work_order_task_repo.list_for_organization(
            organization.id,
            work_order_id=work_order_id,
            status=status,
            assigned_employee_id=assigned_employee_id,
            assigned_team_id=assigned_team_id,
        )
        return filter_scope_rows(
            rows,
            self._user_session,
            scope_type="maintenance",
            permission_code="maintenance.read",
            scope_id_getter=self._scope_anchor_for,
        )

    def get_task(self, work_order_task_id: str) -> MaintenanceWorkOrderTask:
        self._require_read("view maintenance work order task")
        organization = self._active_organization()
        task = self._work_order_task_repo.get(work_order_task_id)
        if task is None or task.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance work order task not found in the active organization.",
                code="MAINTENANCE_WORK_ORDER_TASK_NOT_FOUND",
            )
        self._require_scope_read(self._scope_anchor_for(task), operation_label="view maintenance work order task")
        return task

    def create_task(
        self,
        *,
        work_order_id: str,
        task_name: str,
        task_template_id: str | None = None,
        description: str = "",
        assigned_employee_id: str | None = None,
        assigned_team_id: str | None = None,
        estimated_minutes: int | str | None = None,
        actual_minutes: int | str | None = None,
        required_skill: str = "",
        sequence_no: int | str | None = None,
        is_mandatory: bool = True,
        completion_rule: str | None = None,
        notes: str = "",
    ) -> MaintenanceWorkOrderTask:
        self._require_manage("create maintenance work order task")
        organization = self._active_organization()
        work_order = self._get_work_order(work_order_id, organization=organization)
        self._ensure_work_order_is_mutable(work_order)

        resolved_sequence_no = self._resolve_sequence_no(work_order.id, sequence_no)
        if any(row.sequence_no == resolved_sequence_no for row in self._work_order_task_repo.list_for_organization(organization.id, work_order_id=work_order.id)):
            raise ValidationError(
                "Sequence number already exists on the selected work order.",
                code="MAINTENANCE_WORK_ORDER_TASK_SEQUENCE_EXISTS",
            )

        task = MaintenanceWorkOrderTask.create(
            organization_id=organization.id,
            work_order_id=work_order.id,
            task_template_id=(str(task_template_id or "").strip() or None),
            task_name=normalize_maintenance_name(task_name, label="Task name"),
            description=normalize_optional_text(description),
            assigned_employee_id=assigned_employee_id,
            assigned_team_id=(str(assigned_team_id or "").strip() or None),
            estimated_minutes=coerce_optional_non_negative_int(estimated_minutes, label="Estimated minutes"),
            actual_minutes=coerce_optional_non_negative_int(actual_minutes, label="Actual minutes"),
            required_skill=normalize_optional_text(required_skill),
            sequence_no=resolved_sequence_no,
            is_mandatory=bool(is_mandatory),
            completion_rule=coerce_task_completion_rule(completion_rule),
            notes=normalize_optional_text(notes),
        )
        try:
            self._work_order_task_repo.add(task)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Maintenance work order task could not be saved.",
                code="MAINTENANCE_WORK_ORDER_TASK_SAVE_FAILED",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_work_order_task.create", task)
        return task

    def update_task(
        self,
        work_order_task_id: str,
        *,
        task_name: str | None = None,
        task_template_id: str | None = None,
        description: str | None = None,
        assigned_employee_id: str | None = None,
        assigned_team_id: str | None = None,
        estimated_minutes: int | str | None = None,
        actual_minutes: int | str | None = None,
        required_skill: str | None = None,
        status: str | None = None,
        sequence_no: int | str | None = None,
        is_mandatory: bool | None = None,
        completion_rule: str | None = None,
        notes: str | None = None,
        expected_version: int | None = None,
    ) -> MaintenanceWorkOrderTask:
        self._require_manage("update maintenance work order task")
        task = self.get_task(work_order_task_id)
        work_order = self._get_work_order(task.work_order_id, organization=self._active_organization())
        self._ensure_work_order_is_mutable(work_order)

        if expected_version is not None and task.version != expected_version:
            raise ConcurrencyError(
                "Maintenance work order task changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )

        if task_name is not None:
            task.task_name = normalize_maintenance_name(task_name, label="Task name")
        if task_template_id is not None:
            task.task_template_id = (str(task_template_id or "").strip() or None)
        if description is not None:
            task.description = normalize_optional_text(description)
        if assigned_employee_id is not None:
            task.assigned_employee_id = assigned_employee_id
        if assigned_team_id is not None:
            task.assigned_team_id = (str(assigned_team_id or "").strip() or None)
        if estimated_minutes is not None:
            task.estimated_minutes = coerce_optional_non_negative_int(estimated_minutes, label="Estimated minutes")
        if actual_minutes is not None:
            task.actual_minutes = coerce_optional_non_negative_int(actual_minutes, label="Actual minutes")
        if required_skill is not None:
            task.required_skill = normalize_optional_text(required_skill)
        if is_mandatory is not None:
            task.is_mandatory = bool(is_mandatory)
        if completion_rule is not None:
            task.completion_rule = coerce_task_completion_rule(completion_rule)
        if notes is not None:
            task.notes = normalize_optional_text(notes)

        if sequence_no is not None:
            resolved_sequence_no = self._resolve_sequence_no(task.work_order_id, sequence_no)
            sibling_rows = self._work_order_task_repo.list_for_organization(
                task.organization_id,
                work_order_id=task.work_order_id,
            )
            if any(row.sequence_no == resolved_sequence_no and row.id != task.id for row in sibling_rows):
                raise ValidationError(
                    "Sequence number already exists on the selected work order.",
                    code="MAINTENANCE_WORK_ORDER_TASK_SEQUENCE_EXISTS",
                )
            task.sequence_no = resolved_sequence_no

        if status is not None:
            new_status = coerce_work_order_task_status(status)
            self._validate_work_order_task_status_transition(task.status, new_status)
            if new_status == MaintenanceWorkOrderTaskStatus.COMPLETED:
                self._validate_task_completion(task)
            task.status = new_status
            now = datetime.now(timezone.utc)
            if new_status == MaintenanceWorkOrderTaskStatus.IN_PROGRESS and task.started_at is None:
                task.started_at = now
            if new_status in {
                MaintenanceWorkOrderTaskStatus.COMPLETED,
                MaintenanceWorkOrderTaskStatus.SKIPPED,
            } and task.completed_at is None:
                task.completed_at = now

        task.updated_at = datetime.now(timezone.utc)

        try:
            self._work_order_task_repo.update(task)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Maintenance work order task could not be updated.",
                code="MAINTENANCE_WORK_ORDER_TASK_SAVE_FAILED",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_work_order_task.update", task)
        return task

    def _active_organization(self) -> Organization:
        organization = self._organization_repo.get_active()
        if organization is None:
            raise NotFoundError("Active organization not found.", code="ORGANIZATION_NOT_FOUND")
        return organization

    def _get_work_order(self, work_order_id: str, *, organization: Organization) -> MaintenanceWorkOrder:
        work_order = self._work_order_repo.get(work_order_id)
        if work_order is None or work_order.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance work order not found in the active organization.",
                code="MAINTENANCE_WORK_ORDER_NOT_FOUND",
            )
        return work_order

    def _resolve_sequence_no(self, work_order_id: str, sequence_no: int | str | None) -> int:
        if sequence_no not in (None, ""):
            resolved = int(sequence_no)
            if resolved <= 0:
                raise ValidationError(
                    "Sequence number must be greater than zero.",
                    code="MAINTENANCE_WORK_ORDER_TASK_SEQUENCE_INVALID",
                )
            return resolved
        existing_rows = self._work_order_task_repo.list_for_organization(
            self._active_organization().id,
            work_order_id=work_order_id,
        )
        highest = max((row.sequence_no for row in existing_rows), default=0)
        return highest + 1

    def _ensure_work_order_is_mutable(self, work_order: MaintenanceWorkOrder) -> None:
        if work_order.status in {MaintenanceWorkOrderStatus.CANCELLED, MaintenanceWorkOrderStatus.CLOSED}:
            raise BusinessRuleError(
                "Tasks cannot be changed once the work order is cancelled or closed.",
                code="MAINTENANCE_WORK_ORDER_NOT_MUTABLE",
            )

    def _validate_task_completion(self, task: MaintenanceWorkOrderTask) -> None:
        step_repo = self._work_order_task_step_repo
        if task.completion_rule == MaintenanceTaskCompletionRule.NO_STEPS_REQUIRED:
            return
        if step_repo is None:
            raise ValidationError(
                "Work order task step repository is required for step-based completion checks.",
                code="MAINTENANCE_WORK_ORDER_TASK_STEPS_REQUIRED",
            )
        steps = step_repo.list_for_organization(
            task.organization_id,
            work_order_task_id=task.id,
        )
        if not task_steps_satisfy_completion_rule(task, steps):
            raise ValidationError(
                "All required steps must be completed before the task can be completed.",
                code="MAINTENANCE_WORK_ORDER_TASK_STEPS_INCOMPLETE",
            )

    def _scope_anchor_for(self, task: MaintenanceWorkOrderTask) -> str:
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

    def _record_change(self, action: str, task: MaintenanceWorkOrderTask) -> None:
        record_audit(
            self,
            action=action,
            entity_type="maintenance_work_order_task",
            entity_id=task.id,
            details={
                "organization_id": task.organization_id,
                "work_order_id": task.work_order_id,
                "task_name": task.task_name,
                "sequence_no": task.sequence_no,
                "status": task.status.value,
                "completion_rule": task.completion_rule.value,
                "assigned_employee_id": task.assigned_employee_id,
                "assigned_team_id": task.assigned_team_id,
            },
        )
        domain_events.domain_changed.emit(
            DomainChangeEvent(
                category="module",
                scope_code="maintenance_management",
                entity_type="maintenance_work_order_task",
                entity_id=task.id,
                source_event="maintenance_work_order_tasks_changed",
            )
        )

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.read", operation_label=operation_label)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.manage", operation_label=operation_label)


__all__ = ["MaintenanceWorkOrderTaskService"]
