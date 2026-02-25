# core/services/dashboard_service.py
from __future__ import annotations

from core.events.domain_events import domain_events
from core.services.dashboard.alerts import DashboardAlertsMixin
from core.services.dashboard.burndown import DashboardBurndownMixin
from core.services.dashboard.evm import DashboardEvmMixin
from core.services.dashboard.models import BurndownPoint, DashboardData, DashboardEVM, UpcomingTask
from core.services.dashboard.upcoming import DashboardUpcomingMixin
from core.services.project.service import ProjectService
from core.services.reporting.service import ReportingService
from core.services.resource import ResourceService
from core.services.scheduling.engine import SchedulingEngine
from core.services.scheduling.leveling_models import (
    ResourceConflict,
    ResourceLevelingAction,
    ResourceLevelingResult,
)
from core.services.task.service import TaskService
from core.services.work_calendar.engine import WorkCalendarEngine


class DashboardService(
    DashboardAlertsMixin,
    DashboardUpcomingMixin,
    DashboardBurndownMixin,
    DashboardEvmMixin,
):
    """
    Aggregates data for the Dashboard tab.
    """

    def __init__(
        self,
        reporting_service: ReportingService,
        task_service: TaskService,
        project_service: ProjectService,
        resource_service: ResourceService,
        scheduling_engine: SchedulingEngine,
        work_calendar_engine: WorkCalendarEngine,
    ):
        self._reporting: ReportingService = reporting_service
        self._tasks: TaskService = task_service
        self._projects: ProjectService = project_service
        self._resources: ResourceService = resource_service
        self._sched: SchedulingEngine = scheduling_engine
        self._calendar: WorkCalendarEngine = work_calendar_engine

    def get_dashboard_data(self, project_id: str, baseline_id: str | None = None) -> DashboardData:
        self._sched.recalculate_project_schedule(project_id)

        kpi = self._reporting.get_project_kpis(project_id)
        resource_load = self._reporting.get_resource_load_summary(project_id)
        alerts = self._build_alerts(project_id, kpi, resource_load)
        upcoming = self._build_upcoming_tasks(project_id)
        burndown = self._build_burndown(project_id)
        cost_sources = self._reporting.get_project_cost_source_breakdown(project_id)
        evm_obj = self._build_evm(project_id, baseline_id=baseline_id)

        return DashboardData(
            kpi=kpi,
            alerts=alerts,
            resource_load=resource_load,
            burndown=burndown,
            cost_sources=cost_sources,
            evm=evm_obj,
            upcoming_tasks=upcoming,
        )

    def preview_resource_conflicts(
        self,
        project_id: str,
        threshold_percent: float = 100.0,
    ) -> list[ResourceConflict]:
        self._sched.recalculate_project_schedule(project_id)
        return self._sched.preview_resource_conflicts(
            project_id=project_id,
            threshold_percent=threshold_percent,
        )

    def auto_level_overallocations(
        self,
        project_id: str,
        max_iterations: int = 60,
        threshold_percent: float = 100.0,
    ) -> ResourceLevelingResult:
        result = self._sched.auto_level_resources(
            project_id=project_id,
            max_iterations=max_iterations,
            threshold_percent=threshold_percent,
        )
        self._sched.recalculate_project_schedule(project_id)
        if result.actions:
            domain_events.tasks_changed.emit(project_id)
        return result

    def manually_shift_task_for_leveling(
        self,
        project_id: str,
        task_id: str,
        shift_working_days: int = 1,
        reason: str = "Manual dashboard leveling",
    ) -> ResourceLevelingAction:
        action = self._sched.resolve_resource_conflict_manual(
            project_id=project_id,
            task_id=task_id,
            shift_working_days=shift_working_days,
            reason=reason,
        )
        self._sched.recalculate_project_schedule(project_id)
        domain_events.tasks_changed.emit(project_id)
        return action


__all__ = [
    "DashboardService",
    "DashboardData",
    "DashboardEVM",
    "UpcomingTask",
    "BurndownPoint",
]
