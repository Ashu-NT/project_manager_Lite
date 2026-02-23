# core/services/dashboard_service.py
from __future__ import annotations

from core.services.dashboard.alerts import DashboardAlertsMixin
from core.services.dashboard.burndown import DashboardBurndownMixin
from core.services.dashboard.evm import DashboardEvmMixin
from core.services.dashboard.models import BurndownPoint, DashboardData, DashboardEVM, UpcomingTask
from core.services.dashboard.upcoming import DashboardUpcomingMixin
from core.services.project.service import ProjectService
from core.services.reporting.service import ReportingService
from core.services.resource import ResourceService
from core.services.scheduling.engine import SchedulingEngine
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
        evm_obj = self._build_evm(project_id, baseline_id=baseline_id)

        return DashboardData(
            kpi=kpi,
            alerts=alerts,
            resource_load=resource_load,
            burndown=burndown,
            evm=evm_obj,
            upcoming_tasks=upcoming,
        )


__all__ = [
    "DashboardService",
    "DashboardData",
    "DashboardEVM",
    "UpcomingTask",
    "BurndownPoint",
]
