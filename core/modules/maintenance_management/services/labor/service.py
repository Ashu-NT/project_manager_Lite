from __future__ import annotations

from datetime import date

from core.modules.maintenance_management.services.work_order_task import MaintenanceWorkOrderTaskService
from core.platform.auth.authorization import require_any_permission
from core.platform.common.exceptions import ValidationError
from core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from core.platform.time import TimeService
from core.platform.time.domain import TimeEntry


class MaintenanceLaborService(TimeService):
    """Maintenance-facing labor booking service on the shared time-entry seam."""

    def __init__(
        self,
        *args,
        work_order_task_service: MaintenanceWorkOrderTaskService,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._work_order_task_service = work_order_task_service

    def list_task_labor_entries(self, work_order_task_id: str) -> list[TimeEntry]:
        self._work_order_task_service.get_task(work_order_task_id)
        return self.list_time_entries_for_work_allocation(work_order_task_id)

    def add_task_labor_entry(
        self,
        *,
        work_order_task_id: str,
        entry_date: date,
        hours: float,
        note: str = "",
    ) -> TimeEntry:
        task = self._work_order_task_service.get_task(work_order_task_id)
        if not (task.assigned_employee_id or "").strip():
            raise ValidationError(
                "Assign an employee to the task before booking labor.",
                code="MAINTENANCE_TASK_ASSIGNMENT_REQUIRED",
            )
        entry = self.add_work_entry(
            work_order_task_id,
            entry_date=entry_date,
            hours=hours,
            note=note,
        )
        self._emit_labor_change(task.id)
        return entry

    def _emit_labor_change(self, work_order_task_id: str) -> None:
        domain_events.domain_changed.emit(
            DomainChangeEvent(
                category="module",
                scope_code="maintenance_management",
                entity_type="maintenance_work_order_task_labor",
                entity_id=work_order_task_id,
                source_event="maintenance_task_labor_changed",
            )
        )

    def _require_time_read_permission(self, operation_label: str) -> None:
        require_any_permission(
            self._user_session,
            ("time.read", "maintenance.read"),
            operation_label=operation_label,
        )

    def _require_time_manage_permission(self, operation_label: str) -> None:
        require_any_permission(
            self._user_session,
            ("time.manage", "maintenance.manage"),
            operation_label=operation_label,
        )


__all__ = ["MaintenanceLaborService"]
