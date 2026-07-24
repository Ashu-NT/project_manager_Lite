from __future__ import annotations

from src.core.platform.calendar.application.calendar_protocol import CalendarProtocol

from dataclasses import dataclass, field
from datetime import date

from src.core.modules.project_management.contracts.repositories.resource import ResourceRepository
from src.core.modules.project_management.contracts.repositories.task import (
    AssignmentRepository,
    TaskRepository,
)
from src.core.modules.project_management.contracts.repositories.project import (
    ProjectRepository,
)
from src.core.modules.project_management.domain.resources.resource import Resource
from src.core.modules.project_management.application.resources.resource_availability_service import (
    ResourceAvailabilityService,
    ResourceAvailabilityWindow,
)
from src.core.platform.common.exceptions import BusinessRuleError


@dataclass
class ResourceDemandEntry:
    resource_id: str
    resource_name: str
    project_id: str
    project_name: str
    from_date: date | None
    to_date: date | None
    total_allocation_percent: float


@dataclass
class ResourcePoolSummary:
    """
    Portfolio-level demand vs capacity summary for a single resource.
    """
    resource_id: str
    resource_name: str
    capacity_percent: float
    demands: list[ResourceDemandEntry]
    peak_load_percent: float
    average_load_percent: float
    overloaded: bool

    @property
    def total_demand_percent(self) -> float:
        return sum(d.total_allocation_percent for d in self.demands)


@dataclass
class PortfolioResourcePoolReport:
    """
    Cross-project resource demand and capacity report for a portfolio view.
    """
    from_date: date
    to_date: date
    pool: list[ResourcePoolSummary]

    @property
    def overloaded_resources(self) -> list[ResourcePoolSummary]:
        return [r for r in self.pool if r.overloaded]

    @property
    def utilization_by_resource(self) -> dict[str, float]:
        return {r.resource_id: r.average_load_percent for r in self.pool}


class PortfolioResourcePoolService:
    """
    Portfolio-level resource pool analysis.

    Shows shared resource demand across all active projects, enabling PMO-level
    capacity vs demand visibility and prioritization decisions.

    Builds on ResourceAvailabilityService for per-resource load calculation
    and adds project-level attribution and portfolio aggregation.
    """

    def __init__(
        self,
        resource_repo: ResourceRepository,
        assignment_repo: AssignmentRepository,
        task_repo: TaskRepository,
        project_repo: ProjectRepository,
        calendar: CalendarProtocol,
        tenant_context_service=None,
    ) -> None:
        self._resources = resource_repo
        self._assignments = assignment_repo
        self._tasks = task_repo
        self._projects = project_repo
        self._calendar = calendar
        self._tenant_context_service = tenant_context_service
        self._availability = ResourceAvailabilityService(
            resource_repo=resource_repo,
            assignment_repo=assignment_repo,
            task_repo=task_repo,
            calendar=calendar,
        )

    def get_pool_report(
        self,
        from_date: date,
        to_date: date,
        resource_ids: list[str] | None = None,
    ) -> PortfolioResourcePoolReport:
        """
        Build a portfolio resource pool report for the given date range.

        If resource_ids is None, includes all active resources.
        """
        self._active_organization_id(operation_label="build portfolio resource pool")
        if resource_ids is None:
            all_resources = self._resources.list()
            resource_ids = [r.id for r in all_resources if getattr(r, "is_active", True)]
        else:
            scoped_resource_ids = {
                resource.id
                for resource in self._resources.list()
            }
            resource_ids = [resource_id for resource_id in resource_ids if resource_id in scoped_resource_ids]

        summaries: list[ResourcePoolSummary] = []
        for rid in resource_ids:
            summary = self._build_summary(rid, from_date, to_date)
            if summary is not None:
                summaries.append(summary)

        return PortfolioResourcePoolReport(
            from_date=from_date,
            to_date=to_date,
            pool=summaries,
        )

    def get_resource_demand_by_project(
        self,
        resource_id: str,
        from_date: date,
        to_date: date,
    ) -> list[ResourceDemandEntry]:
        """Return per-project demand breakdown for a single resource."""
        return self._build_demands(resource_id, from_date, to_date)

    # ── internal ────────────────────────────────────────────────────────────

    def _build_summary(
        self,
        resource_id: str,
        from_date: date,
        to_date: date,
    ) -> ResourcePoolSummary | None:
        resource = self._resources.get(resource_id)
        if resource is None:
            return None

        capacity = float(getattr(resource, "capacity_percent", 100.0) or 100.0)
        if capacity <= 0:
            capacity = 100.0

        availability: ResourceAvailabilityWindow = self._availability._compute_window(
            resource_id, from_date, to_date
        )  # type: ignore[assignment]
        if availability is None:
            return None

        demands = self._build_demands(resource_id, from_date, to_date)

        return ResourcePoolSummary(
            resource_id=resource_id,
            resource_name=resource.name,
            capacity_percent=capacity,
            demands=demands,
            peak_load_percent=availability.peak_load_percent,
            average_load_percent=availability.average_load_percent,
            overloaded=not availability.is_available,
        )

    def _build_demands(
        self,
        resource_id: str,
        from_date: date,
        to_date: date,
    ) -> list[ResourceDemandEntry]:
        assignments = self._assignments.list_by_resource(resource_id)
        demands: list[ResourceDemandEntry] = []
        seen_projects: dict[str, str] = {}  # project_id → project_name

        for asgn in assignments:
            task = self._tasks.get(asgn.task_id)
            if task is None:
                continue
            task_start = task.start_date or task.actual_start
            task_end = task.end_date or task.actual_end
            if task_start is None or task_end is None:
                continue
            # Only include tasks that overlap the requested window
            if task_end < from_date or task_start > to_date:
                continue

            project_id = task.project_id
            if project_id not in seen_projects:
                project = self._projects.get(project_id)
                seen_projects[project_id] = project.name if project else project_id

            demands.append(ResourceDemandEntry(
                resource_id=resource_id,
                resource_name="",  # caller can look up from pool summary
                project_id=project_id,
                project_name=seen_projects[project_id],
                from_date=max(task_start, from_date),
                to_date=min(task_end, to_date),
                total_allocation_percent=float(asgn.allocation_percent or 100.0),
            ))

        return demands

    def _active_organization_id(self, *, operation_label: str) -> str:
        tenant_context = self._tenant_context_service
        if tenant_context is None:
            raise BusinessRuleError(
                f"Active organization context is required for {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return tenant_context.require_active_organization_id(operation_label=operation_label)


__all__ = [
    "PortfolioResourcePoolService",
    "PortfolioResourcePoolReport",
    "ResourcePoolSummary",
    "ResourceDemandEntry",
]
