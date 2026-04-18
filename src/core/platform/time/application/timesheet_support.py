from __future__ import annotations

import calendar
from datetime import date
from typing import Protocol

from src.core.platform.auth.authorization import require_any_permission
from core.platform.common.exceptions import NotFoundError, ValidationError
from src.core.platform.org.contracts import EmployeeRepository
from src.core.platform.time.contracts import (
    TimeEntryRepository,
    TimesheetPeriodRepository,
    WorkAllocationRecord,
    WorkAllocationRepository,
    WorkOwnerRecord,
    WorkOwnerRepository,
    WorkResourceRecord,
    WorkResourceRepository,
)
from src.core.platform.time.domain import TimeEntry, TimesheetPeriod, TimesheetPeriodStatus


class _LegacySeedContext(Protocol):
    name: str
    start_date: date | None
    actual_start: date | None


class TimesheetSupportMixin:
    _work_allocation_repo: WorkAllocationRepository
    _work_owner_repo: WorkOwnerRepository
    _resource_repo: WorkResourceRepository
    _employee_repo: EmployeeRepository | None
    _time_entry_repo: TimeEntryRepository | None
    _timesheet_period_repo: TimesheetPeriodRepository | None

    def _require_time_entry(self, entry_id: str) -> TimeEntry:
        if self._time_entry_repo is None:
            raise NotFoundError("Time entry repository is not configured.", code="TIME_ENTRY_REPO_MISSING")
        entry = self._time_entry_repo.get(entry_id)
        if not entry:
            raise NotFoundError("Time entry not found.", code="TIME_ENTRY_NOT_FOUND")
        return entry

    def _require_time_read_permission(self, operation_label: str) -> None:
        require_any_permission(
            self._user_session,
            ("time.read", "task.read"),
            operation_label=operation_label,
        )

    def _require_time_manage_permission(self, operation_label: str) -> None:
        require_any_permission(
            self._user_session,
            ("time.manage", "task.manage"),
            operation_label=operation_label,
        )

    def _load_work_allocation_context(
        self,
        work_allocation_id: str,
    ) -> tuple[WorkAllocationRecord, WorkOwnerRecord | None, WorkResourceRecord | None]:
        work_allocation = self._work_allocation_repo.get(work_allocation_id)
        if not work_allocation:
            raise NotFoundError("Work allocation not found.", code="WORK_ALLOCATION_NOT_FOUND")
        work_owner = self._load_work_owner_for_allocation(work_allocation, strict=True)
        resource = self._resource_repo.get(work_allocation.resource_id)
        return work_allocation, work_owner, resource

    def _load_assignment_context(
        self,
        assignment_id: str,
    ) -> tuple[WorkAllocationRecord, WorkOwnerRecord | None, WorkResourceRecord | None]:
        return self._load_work_allocation_context(assignment_id)

    def _load_work_owner_for_allocation(
        self,
        work_allocation: WorkAllocationRecord,
        *,
        strict: bool,
    ) -> WorkOwnerRecord | None:
        owner_record_id = self._resolve_work_owner_record_id(work_allocation)
        if not owner_record_id:
            return None
        owner = self._work_owner_repo.get(owner_record_id)
        if owner is None and strict:
            raise NotFoundError("Work owner not found.", code="WORK_OWNER_NOT_FOUND")
        return owner

    @staticmethod
    def _normalize_text(value: object | None) -> str:
        return str(value or "").strip()

    def _resolve_work_owner_type(self, work_allocation: WorkAllocationRecord) -> str:
        explicit = self._normalize_text(getattr(work_allocation, "owner_type", None))
        if explicit:
            return explicit
        legacy_task_id = self._normalize_text(getattr(work_allocation, "task_id", None))
        if legacy_task_id:
            return "task_assignment"
        return "work_allocation"

    def _resolve_work_owner_id(self, work_allocation: WorkAllocationRecord) -> str | None:
        explicit = self._normalize_text(getattr(work_allocation, "owner_id", None))
        if explicit:
            return explicit
        if self._resolve_work_owner_type(work_allocation) == "task_assignment":
            allocation_id = self._normalize_text(getattr(work_allocation, "id", None))
            if allocation_id:
                return allocation_id
        legacy_task_id = self._normalize_text(getattr(work_allocation, "task_id", None))
        if legacy_task_id:
            return legacy_task_id
        return self._normalize_text(getattr(work_allocation, "id", None)) or None

    def _resolve_work_owner_record_id(self, work_allocation: WorkAllocationRecord) -> str | None:
        explicit = self._normalize_text(getattr(work_allocation, "work_owner_id", None))
        if explicit:
            return explicit
        legacy_task_id = self._normalize_text(getattr(work_allocation, "task_id", None))
        if legacy_task_id:
            return legacy_task_id
        explicit_owner_id = self._normalize_text(getattr(work_allocation, "owner_id", None))
        if explicit_owner_id:
            return explicit_owner_id
        return None

    def _resolve_work_owner_label(
        self,
        work_allocation: WorkAllocationRecord,
        work_owner: WorkOwnerRecord | None,
    ) -> str:
        if work_owner is not None:
            label = self._normalize_text(getattr(work_owner, "name", None))
            if label:
                return label
        explicit = self._normalize_text(getattr(work_allocation, "owner_label", None))
        if explicit:
            return explicit
        owner_id = self._resolve_work_owner_id(work_allocation)
        if owner_id:
            return owner_id
        return self._normalize_text(getattr(work_allocation, "id", None))

    def _resolve_work_scope_type(
        self,
        work_allocation: WorkAllocationRecord,
        work_owner: WorkOwnerRecord | None,
    ) -> str | None:
        explicit = self._normalize_text(getattr(work_allocation, "scope_type", None))
        if explicit:
            return explicit
        owner_scope_type = self._normalize_text(getattr(work_owner, "scope_type", None))
        if owner_scope_type:
            return owner_scope_type
        if self._normalize_text(getattr(work_owner, "project_id", None)):
            return "project"
        return None

    def _resolve_work_scope_id(
        self,
        work_allocation: WorkAllocationRecord,
        work_owner: WorkOwnerRecord | None,
    ) -> str | None:
        explicit = self._normalize_text(getattr(work_allocation, "scope_id", None))
        if explicit:
            return explicit
        owner_scope_id = self._normalize_text(getattr(work_owner, "scope_id", None))
        if owner_scope_id:
            return owner_scope_id
        project_id = self._normalize_text(getattr(work_owner, "project_id", None))
        if project_id:
            return project_id
        return None

    def _resolve_entry_project_id(
        self,
        *,
        entry: TimeEntry | None = None,
        work_allocation: WorkAllocationRecord | None = None,
        work_owner: WorkOwnerRecord | None = None,
    ) -> str | None:
        if entry is not None and entry.scope_type == "project" and self._normalize_text(entry.scope_id):
            return self._normalize_text(entry.scope_id)
        if work_allocation is not None:
            scope_type = self._resolve_work_scope_type(work_allocation, work_owner)
            scope_id = self._resolve_work_scope_id(work_allocation, work_owner)
            if scope_type == "project" and scope_id:
                return scope_id
        if entry is None:
            return None
        work_allocation_id = self._normalize_text(entry.work_allocation_id) or self._normalize_text(entry.assignment_id)
        if not work_allocation_id:
            return None
        linked_allocation = self._work_allocation_repo.get(work_allocation_id)
        if linked_allocation is None:
            return None
        linked_owner = self._load_work_owner_for_allocation(linked_allocation, strict=False)
        scope_type = self._resolve_work_scope_type(linked_allocation, linked_owner)
        scope_id = self._resolve_work_scope_id(linked_allocation, linked_owner)
        if scope_type == "project" and scope_id:
            return scope_id
        return None

    def _legacy_assignment_id_for_work_allocation(self, work_allocation: WorkAllocationRecord) -> str | None:
        if self._resolve_work_owner_type(work_allocation) != "task_assignment":
            return None
        return self._normalize_text(getattr(work_allocation, "id", None)) or None

    def _resolve_work_entry_context(
        self,
        *,
        work_allocation: WorkAllocationRecord,
        work_owner: WorkOwnerRecord | None,
        resource: WorkResourceRecord | None,
    ) -> dict[str, str | None]:
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
            "owner_type": self._resolve_work_owner_type(work_allocation),
            "owner_id": self._resolve_work_owner_id(work_allocation),
            "owner_label": self._resolve_work_owner_label(work_allocation, work_owner),
            "scope_type": self._resolve_work_scope_type(work_allocation, work_owner),
            "scope_id": self._resolve_work_scope_id(work_allocation, work_owner),
            "employee_id": employee_id,
            "department_id": department_id,
            "department_name": department_name,
            "site_id": site_id,
            "site_name": site_name,
        }

    def _sync_work_allocation_hours_from_entries(self, work_allocation_id: str) -> None:
        if self._time_entry_repo is None:
            return
        work_allocation = self._work_allocation_repo.get(work_allocation_id)
        if not work_allocation:
            raise NotFoundError("Work allocation not found.", code="WORK_ALLOCATION_NOT_FOUND")
        entries = self._time_entry_repo.list_by_work_allocation(work_allocation_id)
        if hasattr(work_allocation, "hours_logged"):
            work_allocation.hours_logged = sum(float(item.hours or 0.0) for item in entries)
        self._work_allocation_repo.update(work_allocation)

    def _sync_assignment_hours_from_entries(self, assignment_id: str) -> None:
        self._sync_work_allocation_hours_from_entries(assignment_id)

    def _seed_legacy_hours_entry(
        self,
        work_allocation: WorkAllocationRecord,
        work_owner: _LegacySeedContext | WorkOwnerRecord | None,
        resource: WorkResourceRecord | None,
    ) -> TimeEntry | None:
        if self._time_entry_repo is None:
            return None
        if self._time_entry_repo.list_by_work_allocation(work_allocation.id):
            return None
        hours = float(getattr(work_allocation, "hours_logged", 0.0) or 0.0)
        if hours <= 0:
            return None
        legacy_date = self._resolve_legacy_time_entry_date(work_owner)
        self._ensure_timesheet_period_editable(
            resource_id=work_allocation.resource_id,
            entry_date=legacy_date,
            operation_label="seed legacy timesheet entry",
        )
        seeded_entry = TimeEntry.create(
            work_allocation_id=work_allocation.id,
            assignment_id=self._legacy_assignment_id_for_work_allocation(work_allocation),
            entry_date=legacy_date,
            hours=hours,
            note="Opening balance migrated from existing logged hours.",
            author_username="system",
            **self._resolve_work_entry_context(
                work_allocation=work_allocation,
                work_owner=work_owner,
                resource=resource,
            ),
        )
        self._time_entry_repo.add(seeded_entry)
        self._session.flush()
        self._sync_work_allocation_hours_from_entries(work_allocation.id)
        return seeded_entry

    @staticmethod
    def _resolve_legacy_time_entry_date(work_owner: _LegacySeedContext | WorkOwnerRecord | None) -> date:
        actual_start = getattr(work_owner, "actual_start", None) if work_owner is not None else None
        start_date = getattr(work_owner, "start_date", None) if work_owner is not None else None
        return actual_start or start_date or date.today()

    def _build_time_entry_audit_details(
        self,
        *,
        work_allocation: WorkAllocationRecord,
        work_owner: WorkOwnerRecord | None,
        resource_name: str,
        entry: TimeEntry,
        extra: dict[str, object] | None = None,
    ) -> dict[str, object]:
        owner_label = entry.owner_label or self._resolve_work_owner_label(work_allocation, work_owner)
        details: dict[str, object] = {
            "work_allocation_id": entry.work_allocation_id,
            "resource_name": resource_name or work_allocation.resource_id,
            "hours": entry.hours,
            "entry_date": str(entry.entry_date),
            "owner_type": entry.owner_type,
        }
        if owner_label:
            details["owner_label"] = owner_label
            if entry.owner_type == "task_assignment":
                details["task_name"] = owner_label
        if entry.owner_id:
            details["owner_id"] = entry.owner_id
        if entry.scope_type:
            details["scope_type"] = entry.scope_type
        if entry.scope_id:
            details["scope_id"] = entry.scope_id
            if entry.scope_type == "project":
                details["project_id"] = entry.scope_id
        if entry.employee_id:
            details["employee_id"] = entry.employee_id
        if getattr(entry, "department_id", None):
            details["department_id"] = entry.department_id
        if entry.department_name:
            details["department_name"] = entry.department_name
        if getattr(entry, "site_id", None):
            details["site_id"] = entry.site_id
        if entry.site_name:
            details["site_name"] = entry.site_name
        for key, value in (extra or {}).items():
            if value is not None:
                details[key] = value
        return details

    @staticmethod
    def _validate_time_entry_hours(hours: float) -> float:
        resolved = float(hours or 0.0)
        if resolved <= 0:
            raise ValidationError("Time entry hours must be greater than zero.")
        return resolved

    def _require_timesheet_period(self, period_id: str) -> TimesheetPeriod:
        if self._timesheet_period_repo is None:
            raise NotFoundError("Timesheet period repository is not configured.", code="TIMESHEET_PERIOD_REPO_MISSING")
        period = self._timesheet_period_repo.get(period_id)
        if not period:
            raise NotFoundError("Timesheet period not found.", code="TIMESHEET_PERIOD_NOT_FOUND")
        return period

    def _get_or_create_timesheet_period(self, *, resource_id: str, period_start: date) -> TimesheetPeriod:
        if self._timesheet_period_repo is None:
            raise ValidationError("Timesheet period repository is not configured.")
        normalized_start, normalized_end = self._timesheet_period_bounds(period_start)
        period = self._timesheet_period_repo.get_by_resource_period(resource_id, normalized_start)
        if period is not None:
            return period
        period = TimesheetPeriod.create(
            resource_id=resource_id,
            period_start=normalized_start,
            period_end=normalized_end,
        )
        self._timesheet_period_repo.add(period)
        self._session.flush()
        return period

    def _lookup_timesheet_period(self, *, resource_id: str, period_start: date) -> TimesheetPeriod | None:
        if self._timesheet_period_repo is None:
            return None
        normalized_start, _ = self._timesheet_period_bounds(period_start)
        return self._timesheet_period_repo.get_by_resource_period(resource_id, normalized_start)

    def _ensure_timesheet_period_editable(
        self,
        *,
        resource_id: str,
        entry_date: date,
        operation_label: str,
    ) -> None:
        period = self._lookup_timesheet_period(resource_id=resource_id, period_start=entry_date)
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
    def _timesheet_period_bounds(period_date: date) -> tuple[date, date]:
        normalized_start = period_date.replace(day=1)
        last_day = calendar.monthrange(normalized_start.year, normalized_start.month)[1]
        normalized_end = normalized_start.replace(day=last_day)
        return normalized_start, normalized_end

    @staticmethod
    def _sum_entry_hours(entries: list[TimeEntry]) -> float:
        return sum(float(item.hours or 0.0) for item in entries)

    def _build_timesheet_period_audit_details(
        self,
        *,
        period: TimesheetPeriod,
        entry_count: int,
        total_hours: float,
        project_ids: list[str] | None = None,
    ) -> dict[str, object]:
        resource = self._resource_repo.get(period.resource_id)
        details: dict[str, object] = {
            "resource_name": resource.name if resource is not None else period.resource_id,
            "period_start": str(period.period_start),
            "period_end": str(period.period_end),
            "status": period.status.value,
            "entry_count": entry_count,
            "total_hours": total_hours,
        }
        normalized_project_ids = [item for item in (project_ids or []) if str(item).strip()]
        if len(normalized_project_ids) == 1:
            details["project_id"] = normalized_project_ids[0]
        elif normalized_project_ids:
            details["project_ids"] = normalized_project_ids
        return details

    def _project_ids_for_entries(self, entries: list[TimeEntry]) -> list[str]:
        project_ids: set[str] = set()
        for entry in entries:
            if entry.scope_type == "project" and self._normalize_text(entry.scope_id):
                project_ids.add(self._normalize_text(entry.scope_id))
                continue
            project_id = self._resolve_entry_project_id(entry=entry)
            if project_id:
                project_ids.add(project_id)
        return sorted(project_ids)


__all__ = ["TimesheetSupportMixin"]
