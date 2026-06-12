from __future__ import annotations

from src.core.platform.calendar.application.calendar_protocol import CalendarProtocol

from dataclasses import dataclass, field
from datetime import date

from src.core.modules.project_management.contracts.repositories.resource import ResourceRepository
from src.core.modules.project_management.contracts.repositories.task import (
    AssignmentRepository,
    TaskRepository,
)
from src.core.modules.project_management.domain.resources.resource import Resource
from src.core.modules.project_management.domain.tasks.task import Task, TaskAssignment


@dataclass
class ResourceDateLoad:
    """Allocation load on a single resource on a single working day."""
    resource_id: str
    resource_name: str
    check_date: date
    total_allocation_percent: float
    capacity_percent: float
    overloaded: bool
    contributing_tasks: list[str]  # task IDs


@dataclass
class ResourceAvailabilityWindow:
    """
    Summary of a resource's availability across a date range,
    across all projects (multi-project scope).
    """
    resource_id: str
    resource_name: str
    capacity_percent: float
    from_date: date
    to_date: date
    peak_load_percent: float
    average_load_percent: float
    overloaded_days: int
    available_days: int
    daily_loads: list[ResourceDateLoad] = field(default_factory=list)

    @property
    def is_available(self) -> bool:
        return self.peak_load_percent < self.capacity_percent


@dataclass
class MultiProjectAvailabilityReport:
    """Availability summary across all active projects for a set of resources."""
    from_date: date
    to_date: date
    resources: list[ResourceAvailabilityWindow]

    @property
    def overloaded_resources(self) -> list[ResourceAvailabilityWindow]:
        return [r for r in self.resources if not r.is_available]


class ResourceAvailabilityService:
    """
    Multi-project resource availability checker.

    Unlike the single-project leveling preview, this service computes load
    across ALL projects a resource is assigned to, enabling portfolio-level
    capacity planning.

    Workflow:
        report = service.check_availability(resource_ids, from_date, to_date)
        for window in report.overloaded_resources:
            # surface overload warning in assignment UI
    """

    def __init__(
        self,
        resource_repo: ResourceRepository,
        assignment_repo: AssignmentRepository,
        task_repo: TaskRepository,
        calendar: CalendarProtocol,
    ) -> None:
        self._resources: ResourceRepository = resource_repo
        self._assignments: AssignmentRepository = assignment_repo
        self._tasks: TaskRepository = task_repo
        self._calendar: CalendarProtocol = calendar

    def check_availability(
        self,
        resource_ids: list[str],
        from_date: date,
        to_date: date,
    ) -> MultiProjectAvailabilityReport:
        """
        Compute daily load for each resource across ALL projects between from_date and to_date.
        """
        windows: list[ResourceAvailabilityWindow] = []
        for rid in resource_ids:
            window = self._compute_window(rid, from_date, to_date)
            if window is not None:
                windows.append(window)
        return MultiProjectAvailabilityReport(from_date=from_date, to_date=to_date, resources=windows)

    def is_resource_available(
        self,
        resource_id: str,
        planned_start: date,
        planned_finish: date,
        additional_allocation_percent: float = 100.0,
    ) -> tuple[bool, ResourceAvailabilityWindow | None]:
        """
        Quick check: can this resource accept additional_allocation_percent
        throughout the planned window without exceeding capacity?

        Returns (available, window) — window contains daily detail if blocked.
        """
        window = self._compute_window(resource_id, planned_start, planned_finish)
        if window is None:
            return True, None

        resource = self._resources.get(resource_id)
        capacity = float(getattr(resource, "capacity_percent", 100.0) or 100.0) if resource else 100.0
        peak_with_addition = window.peak_load_percent + additional_allocation_percent
        return peak_with_addition <= capacity, window

    # ── internal ────────────────────────────────────────────────────────────

    def _compute_window(
        self,
        resource_id: str,
        from_date: date,
        to_date: date,
    ) -> ResourceAvailabilityWindow | None:
        resource = self._resources.get(resource_id)
        if resource is None:
            return None
        capacity = float(getattr(resource, "capacity_percent", 100.0) or 100.0)
        if capacity <= 0:
            capacity = 100.0

        # All assignments for this resource across all projects
        assignments: list[TaskAssignment] = self._assignments.list_by_resource(resource_id)
        if not assignments:
            working_days = max(0, self._calendar.working_days_between(from_date, to_date))
            return ResourceAvailabilityWindow(
                resource_id=resource_id,
                resource_name=resource.name,
                capacity_percent=capacity,
                from_date=from_date,
                to_date=to_date,
                peak_load_percent=0.0,
                average_load_percent=0.0,
                overloaded_days=0,
                available_days=working_days,
            )

        # Build task map for all assigned tasks
        task_ids = list({a.task_id for a in assignments})
        tasks_by_id: dict[str, Task] = {}
        for tid in task_ids:
            task = self._tasks.get(tid)
            if task:
                tasks_by_id[tid] = task

        # Compute daily load across the window
        daily_loads: list[ResourceDateLoad] = []
        working_days = 0
        overloaded = 0
        total_load = 0.0

        current = from_date
        while current <= to_date:
            if not self._calendar.is_working_day(current):
                current = self._next_day(current)
                continue
            working_days += 1
            day_load = 0.0
            contributing: list[str] = []
            for asgn in assignments:
                task = tasks_by_id.get(asgn.task_id)
                if task is None:
                    continue
                task_start = getattr(task, "start_date", None) or getattr(task, "actual_start", None)
                task_end = getattr(task, "end_date", None) or getattr(task, "actual_end", None)
                if task_start and task_end and task_start <= current <= task_end:
                    day_load += float(asgn.allocation_percent or 100.0)
                    contributing.append(asgn.task_id)
            is_over = day_load > capacity
            if is_over:
                overloaded += 1
            total_load += day_load
            daily_loads.append(ResourceDateLoad(
                resource_id=resource_id,
                resource_name=resource.name,
                check_date=current,
                total_allocation_percent=day_load,
                capacity_percent=capacity,
                overloaded=is_over,
                contributing_tasks=contributing,
            ))
            current = self._next_day(current)

        peak = max((d.total_allocation_percent for d in daily_loads), default=0.0)
        avg = (total_load / working_days) if working_days > 0 else 0.0

        return ResourceAvailabilityWindow(
            resource_id=resource_id,
            resource_name=resource.name,
            capacity_percent=capacity,
            from_date=from_date,
            to_date=to_date,
            peak_load_percent=peak,
            average_load_percent=avg,
            overloaded_days=overloaded,
            available_days=working_days - overloaded,
            daily_loads=daily_loads,
        )

    def _next_day(self, d: date) -> date:
        from datetime import timedelta
        return d + timedelta(days=1)


__all__ = [
    "ResourceAvailabilityService",
    "MultiProjectAvailabilityReport",
    "ResourceAvailabilityWindow",
    "ResourceDateLoad",
]
