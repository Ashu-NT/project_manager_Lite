from __future__ import annotations

import calendar
from datetime import date
from typing import Any

from src.core.platform.common.exceptions import NotFoundError, ValidationError
from src.core.platform.contract.interface.time_management.time.contracts import (
    WorkAllocationRecord,
    WorkOwnerRecord,
    WorkResourceRecord,
)
from src.core.platform.contract.repositories.master_data.employee.contracts import (
    EmployeeRepository,
)
from src.core.platform.contract.repositories.time_management.time.contracts import (
    TimeEntryRepository,
    TimesheetPeriodRepository,
    WorkAllocationRepository,
    WorkOwnerRepository,
    WorkResourceRepository,
)
from src.core.platform.domain.time_management.time import (
    TimeEntry,
    TimesheetPeriod,
    TimesheetPeriodStatus,
)


class TimesheetSupport:
    """Read-side work/period context shared by Time entry, period and query handlers.

    Owns allocation/owner/scope resolution, project attribution, period lookup
    and the period-editability rule. It performs no authorization, no writes
    and owns no transaction.
    """

    def __init__(
        self,
        *,
        work_allocation_repo: WorkAllocationRepository,
        work_owner_repo: WorkOwnerRepository,
        resource_repo: WorkResourceRepository,
        employee_repo: EmployeeRepository | None,
        time_entry_repo: TimeEntryRepository | None,
        timesheet_period_repo: TimesheetPeriodRepository | None,
    ) -> None:
        self._work_allocation_repo = work_allocation_repo
        self._work_owner_repo = work_owner_repo
        self._resource_repo = resource_repo
        self._employee_repo = employee_repo
        self._time_entry_repo = time_entry_repo
        self._timesheet_period_repo = timesheet_period_repo

    def require_time_entry(self, entry_id: str) -> TimeEntry:
        if self._time_entry_repo is None:
            raise NotFoundError("Time entry repository is not configured.", code="TIME_ENTRY_REPO_MISSING")
        entry = self._time_entry_repo.get(entry_id)
        if not entry:
            raise NotFoundError("Time entry not found.", code="TIME_ENTRY_NOT_FOUND")
        return entry

    def load_work_allocation_context(
        self,
        work_allocation_id: str,
    ) -> tuple[WorkAllocationRecord, WorkOwnerRecord | None, WorkResourceRecord | None]:
        work_allocation = self._work_allocation_repo.get(work_allocation_id)
        if not work_allocation:
            raise NotFoundError("Work allocation not found.", code="WORK_ALLOCATION_NOT_FOUND")
        work_owner = self.load_work_owner_for_allocation(work_allocation, strict=True)
        resource = self._resource_repo.get(work_allocation.resource_id)
        return work_allocation, work_owner, resource

    def load_work_owner_for_allocation(
        self,
        work_allocation: WorkAllocationRecord,
        *,
        strict: bool,
    ) -> WorkOwnerRecord | None:
        owner_record_id = self.resolve_work_owner_record_id(work_allocation)
        if not owner_record_id:
            return None
        owner = self._work_owner_repo.get(owner_record_id)
        if owner is None and strict:
            raise NotFoundError("Work owner not found.", code="WORK_OWNER_NOT_FOUND")
        return owner

    @staticmethod
    def normalize_text(value: object | None) -> str:
        return str(value or "").strip()

    def resolve_work_owner_type(self, work_allocation: WorkAllocationRecord) -> str:
        explicit = self.normalize_text(getattr(work_allocation, "owner_type", None))
        if explicit:
            return explicit
        legacy_task_id = self.normalize_text(getattr(work_allocation, "task_id", None))
        if legacy_task_id:
            return "task_assignment"
        return "work_allocation"

    def resolve_work_owner_id(self, work_allocation: WorkAllocationRecord) -> str | None:
        explicit = self.normalize_text(getattr(work_allocation, "owner_id", None))
        if explicit:
            return explicit
        if self.resolve_work_owner_type(work_allocation) == "task_assignment":
            allocation_id = self.normalize_text(getattr(work_allocation, "id", None))
            if allocation_id:
                return allocation_id
        legacy_task_id = self.normalize_text(getattr(work_allocation, "task_id", None))
        if legacy_task_id:
            return legacy_task_id
        return self.normalize_text(getattr(work_allocation, "id", None)) or None

    def resolve_work_owner_record_id(self, work_allocation: WorkAllocationRecord) -> str | None:
        explicit = self.normalize_text(getattr(work_allocation, "work_owner_id", None))
        if explicit:
            return explicit
        legacy_task_id = self.normalize_text(getattr(work_allocation, "task_id", None))
        if legacy_task_id:
            return legacy_task_id
        explicit_owner_id = self.normalize_text(getattr(work_allocation, "owner_id", None))
        if explicit_owner_id:
            return explicit_owner_id
        return None

    def resolve_work_owner_label(
        self,
        work_allocation: WorkAllocationRecord,
        work_owner: WorkOwnerRecord | None,
    ) -> str:
        if work_owner is not None:
            label = self.normalize_text(getattr(work_owner, "name", None))
            if label:
                return label
        explicit = self.normalize_text(getattr(work_allocation, "owner_label", None))
        if explicit:
            return explicit
        owner_id = self.resolve_work_owner_id(work_allocation)
        if owner_id:
            return owner_id
        return self.normalize_text(getattr(work_allocation, "id", None))

    def resolve_work_scope_type(
        self,
        work_allocation: WorkAllocationRecord,
        work_owner: WorkOwnerRecord | None,
    ) -> str | None:
        explicit = self.normalize_text(getattr(work_allocation, "scope_type", None))
        if explicit:
            return explicit
        owner_scope_type = self.normalize_text(getattr(work_owner, "scope_type", None))
        if owner_scope_type:
            return owner_scope_type
        if self.normalize_text(getattr(work_owner, "project_id", None)):
            return "project"
        return None

    def resolve_work_scope_id(
        self,
        work_allocation: WorkAllocationRecord,
        work_owner: WorkOwnerRecord | None,
    ) -> str | None:
        explicit = self.normalize_text(getattr(work_allocation, "scope_id", None))
        if explicit:
            return explicit
        owner_scope_id = self.normalize_text(getattr(work_owner, "scope_id", None))
        if owner_scope_id:
            return owner_scope_id
        project_id = self.normalize_text(getattr(work_owner, "project_id", None))
        if project_id:
            return project_id
        return None

    def resolve_entry_project_id(
        self,
        *,
        entry: TimeEntry | None = None,
        work_allocation: WorkAllocationRecord | None = None,
        work_owner: WorkOwnerRecord | None = None,
    ) -> str | None:
        if entry is not None and entry.scope_type == "project" and self.normalize_text(entry.scope_id):
            return self.normalize_text(entry.scope_id)
        if work_allocation is not None:
            scope_type = self.resolve_work_scope_type(work_allocation, work_owner)
            scope_id = self.resolve_work_scope_id(work_allocation, work_owner)
            if scope_type == "project" and scope_id:
                return scope_id
        if entry is None:
            return None
        work_allocation_id = self.normalize_text(entry.work_allocation_id) or self.normalize_text(entry.assignment_id)
        if not work_allocation_id:
            return None
        linked_allocation = self._work_allocation_repo.get(work_allocation_id)
        if linked_allocation is None:
            return None
        linked_owner = self.load_work_owner_for_allocation(linked_allocation, strict=False)
        scope_type = self.resolve_work_scope_type(linked_allocation, linked_owner)
        scope_id = self.resolve_work_scope_id(linked_allocation, linked_owner)
        if scope_type == "project" and scope_id:
            return scope_id
        return None

    def legacy_assignment_id_for_work_allocation(self, work_allocation: WorkAllocationRecord) -> str | None:
        if self.resolve_work_owner_type(work_allocation) != "task_assignment":
            return None
        return self.normalize_text(getattr(work_allocation, "id", None)) or None

    def resolve_work_entry_context(
        self,
        *,
        work_allocation: WorkAllocationRecord,
        work_owner: WorkOwnerRecord | None,
        resource: WorkResourceRecord | None,
    ) -> dict[str, Any]:
        employee_id = getattr(resource, "employee_id", None) if resource is not None else None
        department_id = None
        department_name = ""
        site_id = None
        site_name = ""
        if employee_id and self._employee_repo is not None:
            employee = self._employee_repo.get(employee_id)
            if employee is not None:
                department_id = getattr(employee, "department_id", None)
                department_name = (employee.department or "").strip()
                site_id = getattr(employee, "site_id", None)
                site_name = (getattr(employee, "site_name", "") or "").strip()
        return {
            "owner_type": self.resolve_work_owner_type(work_allocation),
            "owner_id": self.resolve_work_owner_id(work_allocation),
            "owner_label": self.resolve_work_owner_label(work_allocation, work_owner),
            "scope_type": self.resolve_work_scope_type(work_allocation, work_owner),
            "scope_id": self.resolve_work_scope_id(work_allocation, work_owner),
            "employee_id": employee_id,
            "department_id": department_id,
            "department_name": department_name,
            "site_id": site_id,
            "site_name": site_name,
        }

    def lookup_timesheet_period(self, *, resource_id: str, period_start: date) -> TimesheetPeriod | None:
        if self._timesheet_period_repo is None:
            return None
        normalized_start, _ = self.timesheet_period_bounds(period_start)
        return self._timesheet_period_repo.get_by_resource_period(resource_id, normalized_start)

    def ensure_timesheet_period_editable(
        self,
        *,
        resource_id: str,
        entry_date: date,
        operation_label: str,
    ) -> None:
        period = self.lookup_timesheet_period(resource_id=resource_id, period_start=entry_date)
        if period is None:
            return
        if period.status not in {
            TimesheetPeriodStatus.SUBMITTED,
            TimesheetPeriodStatus.APPROVED,
            TimesheetPeriodStatus.LOCKED,
        }:
            return
        raise ValidationError(
            f"Cannot {operation_label}: timesheet period {period.period_start.isoformat()} is {period.status.value.lower()}."
        )

    @staticmethod
    def timesheet_period_bounds(period_date: date) -> tuple[date, date]:
        normalized_start = period_date.replace(day=1)
        last_day = calendar.monthrange(normalized_start.year, normalized_start.month)[1]
        normalized_end = normalized_start.replace(day=last_day)
        return normalized_start, normalized_end

    @staticmethod
    def sum_entry_hours(entries: list[TimeEntry]) -> float:
        return sum(float(item.hours or 0.0) for item in entries)

    def project_ids_for_entries(self, entries: list[TimeEntry]) -> list[str]:
        project_ids: set[str] = set()
        for entry in entries:
            if entry.scope_type == "project" and self.normalize_text(entry.scope_id):
                project_ids.add(self.normalize_text(entry.scope_id))
                continue
            project_id = self.resolve_entry_project_id(entry=entry)
            if project_id:
                project_ids.add(project_id)
        return sorted(project_ids)


__all__ = ["TimesheetSupport"]
