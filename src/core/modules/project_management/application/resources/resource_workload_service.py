from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import NotFoundError, ValidationError


MAX_RESOURCE_WORKLOAD_DAYS = 366


def _decimal(value: object) -> Decimal:
    return Decimal(str(value if value not in (None, "") else "0"))


@dataclass(frozen=True, slots=True)
class ResourceWorkloadDayFact:
    work_date: date
    base_capacity_hours: Decimal
    effective_capacity_hours: Decimal
    planned_commitment_hours: Decimal
    remaining_capacity_hours: Decimal
    utilization_percent: Decimal | None
    overallocated: bool
    assignment_count: int


@dataclass(frozen=True, slots=True)
class ResourceWorkloadFact:
    resource_id: str
    start_date: date
    end_date: date
    calendar_source_chain: tuple[str, ...]
    capacity_percent: Decimal
    base_capacity_hours: Decimal
    effective_capacity_hours: Decimal
    planned_commitment_hours: Decimal
    allocated_planned_hours: Decimal
    remaining_capacity_hours: Decimal
    utilization_percent: Decimal | None
    overallocated: bool
    conflict_dates: tuple[date, ...]
    project_count: int
    assignment_count: int
    resource_version: int
    days: tuple[ResourceWorkloadDayFact, ...]


class ResourceWorkloadService:
    """Canonical calendar-backed, multi-project Resource capacity query."""

    def __init__(
        self,
        *,
        resource_repo,
        assignment_repo,
        task_repo,
        availability_service,
        user_session,
    ) -> None:
        self._resources = resource_repo
        self._assignments = assignment_repo
        self._tasks = task_repo
        self._availability = availability_service
        self._user_session = user_session

    def read(
        self,
        resource_id: str,
        *,
        start_date: date,
        end_date: date,
    ) -> ResourceWorkloadFact:
        require_permission(
            self._user_session,
            "resource.read",
            operation_label="view resource availability",
        )
        if end_date < start_date:
            raise ValidationError(
                "Availability end date must be on or after start date.",
                code="RESOURCE_WORKLOAD_RANGE_INVALID",
            )
        day_count = (end_date - start_date).days + 1
        if day_count > MAX_RESOURCE_WORKLOAD_DAYS:
            raise ValidationError(
                f"Availability range cannot exceed {MAX_RESOURCE_WORKLOAD_DAYS} days.",
                code="RESOURCE_WORKLOAD_RANGE_TOO_LARGE",
            )

        resource = self._resources.get(resource_id)
        if resource is None:
            raise NotFoundError("Resource not found.", code="RESOURCE_NOT_FOUND")

        capacity_percent = _decimal(resource.capacity_percent)
        capacity_fraction = capacity_percent / Decimal("100")
        calendar_days = self._availability.get_availability_range(
            resource_id,
            site_id=getattr(resource, "site_id", None),
            department_id=getattr(resource, "department_id", None),
            start=start_date,
            end=end_date,
        )
        calendar_by_date = {day.date: day for day in calendar_days}

        assignments = tuple(self._assignments.list_by_resource(resource_id))
        task_ids = sorted({assignment.task_id for assignment in assignments})
        tasks_by_id = {
            task.id: task for task in self._tasks.list_by_ids(task_ids)
        } if task_ids else {}

        planned_by_date: dict[date, Decimal] = {}
        assignments_by_date: dict[date, set[str]] = {}
        project_ids: set[str] = set()
        relevant_assignment_ids: set[str] = set()
        allocated_planned_hours = Decimal("0")
        for assignment in assignments:
            task = tasks_by_id.get(assignment.task_id)
            if task is None:
                continue
            task_start = getattr(task, "start_date", None)
            task_end = getattr(task, "end_date", None)
            if task_start is None or task_end is None:
                continue
            overlap_start = max(start_date, task_start)
            overlap_end = min(end_date, task_end)
            if overlap_end < overlap_start:
                continue
            project_ids.add(str(task.project_id))
            relevant_assignment_ids.add(str(assignment.id))
            allocated_planned_hours += _decimal(
                getattr(assignment, "allocated_planned_hours", Decimal("0"))
            )
            allocation_fraction = _decimal(assignment.allocation_percent) / Decimal("100")
            current = overlap_start
            while current <= overlap_end:
                calendar_day = calendar_by_date.get(current)
                if calendar_day is not None:
                    raw_hours = _decimal(calendar_day.available_hours)
                    planned_by_date[current] = planned_by_date.get(
                        current, Decimal("0")
                    ) + raw_hours * allocation_fraction
                    assignments_by_date.setdefault(current, set()).add(
                        str(assignment.id)
                    )
                current += timedelta(days=1)

        daily_facts: list[ResourceWorkloadDayFact] = []
        source_chain: tuple[str, ...] = ()
        current = start_date
        while current <= end_date:
            calendar_day = calendar_by_date.get(current)
            base = _decimal(calendar_day.available_hours) if calendar_day else Decimal("0")
            effective = base * capacity_fraction
            planned = planned_by_date.get(current, Decimal("0"))
            remaining = effective - planned
            utilization = (
                planned / effective * Decimal("100") if effective > 0 else None
            )
            if calendar_day is not None and not source_chain and calendar_day.source_chain:
                source_chain = tuple(str(item) for item in calendar_day.source_chain)
            daily_facts.append(
                ResourceWorkloadDayFact(
                    work_date=current,
                    base_capacity_hours=base,
                    effective_capacity_hours=effective,
                    planned_commitment_hours=planned,
                    remaining_capacity_hours=remaining,
                    utilization_percent=utilization,
                    overallocated=planned > effective,
                    assignment_count=len(assignments_by_date.get(current, ())),
                )
            )
            current += timedelta(days=1)

        base_total = sum((day.base_capacity_hours for day in daily_facts), Decimal("0"))
        effective_total = sum(
            (day.effective_capacity_hours for day in daily_facts), Decimal("0")
        )
        planned_total = sum(
            (day.planned_commitment_hours for day in daily_facts), Decimal("0")
        )
        return ResourceWorkloadFact(
            resource_id=resource.id,
            start_date=start_date,
            end_date=end_date,
            calendar_source_chain=source_chain,
            capacity_percent=capacity_percent,
            base_capacity_hours=base_total,
            effective_capacity_hours=effective_total,
            planned_commitment_hours=planned_total,
            allocated_planned_hours=allocated_planned_hours,
            remaining_capacity_hours=effective_total - planned_total,
            utilization_percent=(
                planned_total / effective_total * Decimal("100")
                if effective_total > 0
                else None
            ),
            overallocated=any(day.overallocated for day in daily_facts),
            conflict_dates=tuple(
                day.work_date for day in daily_facts if day.overallocated
            ),
            project_count=len(project_ids),
            assignment_count=len(relevant_assignment_ids),
            resource_version=int(resource.version),
            days=tuple(daily_facts),
        )


__all__ = [
    "MAX_RESOURCE_WORKLOAD_DAYS",
    "ResourceWorkloadDayFact",
    "ResourceWorkloadFact",
    "ResourceWorkloadService",
]
