from __future__ import annotations

from src.core.platform.notifications.domain_events import domain_events
from src.core.platform.access.authorization import require_project_permission
from src.core.platform.auth.authorization import require_permission
from core.modules.project_management.services.common.module_guard import ProjectManagementModuleGuardMixin
from core.modules.project_management.services.dashboard.alerts import DashboardAlertsMixin
from core.modules.project_management.services.dashboard.burndown import DashboardBurndownMixin
from core.modules.project_management.services.dashboard.evm import DashboardEvmMixin
from core.modules.project_management.services.dashboard.register import DashboardRegisterMixin
from core.modules.project_management.services.dashboard.models import BurndownPoint, DashboardData, DashboardEVM, UpcomingTask
from core.modules.project_management.services.dashboard.portfolio import DashboardPortfolioMixin
from core.modules.project_management.services.dashboard.professional import DashboardProfessionalMixin
from core.modules.project_management.services.dashboard.upcoming import DashboardUpcomingMixin
from src.core.modules.project_management.application.projects import ProjectService
from core.modules.project_management.services.reporting.service import ReportingService
from core.modules.project_management.services.register import RegisterService
from core.modules.project_management.services.resource import ResourceService
from core.modules.project_management.services.scheduling.engine import SchedulingEngine
from core.modules.project_management.services.scheduling.leveling_models import ResourceConflict, ResourceLevelingAction, ResourceLevelingResult
from core.modules.project_management.services.task.service import TaskService
from core.modules.project_management.services.work_calendar.engine import WorkCalendarEngine


class DashboardService(
    ProjectManagementModuleGuardMixin,
    DashboardAlertsMixin,
    DashboardUpcomingMixin,
    DashboardBurndownMixin,
    DashboardEvmMixin,
    DashboardRegisterMixin,
    DashboardPortfolioMixin,
    DashboardProfessionalMixin,
):
    def __init__(
        self,
        reporting_service: ReportingService,
        task_service: TaskService,
        project_service: ProjectService,
        resource_service: ResourceService,
        register_service: RegisterService | None,
        scheduling_engine: SchedulingEngine,
        work_calendar_engine: WorkCalendarEngine,
        user_session=None,
        module_catalog_service=None,
    ):
        self._reporting: ReportingService = reporting_service
        self._tasks: TaskService = task_service
        self._projects: ProjectService = project_service
        self._resources: ResourceService = resource_service
        self._registers: RegisterService | None = register_service
        self._sched: SchedulingEngine = scheduling_engine
        self._calendar: WorkCalendarEngine = work_calendar_engine
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def get_dashboard_data(self, project_id: str, baseline_id: str | None = None) -> DashboardData:
        require_permission(self._user_session, "report.view", operation_label="view dashboard")
        require_project_permission(self._user_session, project_id, "report.view", operation_label="view dashboard")
        # Dashboard refresh should be read-only and never contend with task edits.
        schedule = self._sched.recalculate_project_schedule(project_id, persist=False)

        kpi = self._reporting.get_project_kpis(project_id, schedule=schedule)
        resource_load = self._reporting.get_resource_load_summary(project_id)
        alerts = self._build_alerts(project_id, kpi, resource_load)
        upcoming = self._build_upcoming_tasks(project_id)
        burndown = self._build_burndown(project_id)
        milestones = self._build_milestone_health(project_id, schedule=schedule)
        critical_watchlist = self._build_critical_watchlist(project_id, schedule=schedule)
        register_summary = self._build_register_summary(project_id)
        cost_sources = self._reporting.get_project_cost_source_breakdown(project_id)
        evm_obj = self._build_evm(project_id, baseline_id=baseline_id)

        return DashboardData(
            kpi=kpi,
            alerts=alerts,
            resource_load=resource_load,
            burndown=burndown,
            milestone_health=milestones,
            critical_watchlist=critical_watchlist,
            register_summary=register_summary,
            cost_sources=cost_sources,
            evm=evm_obj,
            upcoming_tasks=upcoming,
        )

    def preview_resource_conflicts(
        self,
        project_id: str,
        threshold_percent: float = 100.0,
        *,
        recalculate: bool = True,
    ) -> list[ResourceConflict]:
        require_permission(self._user_session, "report.view", operation_label="view resource conflicts")
        require_project_permission(self._user_session, project_id, "report.view", operation_label="view resource conflicts")
        if recalculate:
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
        *,
        emit_events: bool = True,
    ) -> ResourceLevelingResult:
        require_permission(
            self._user_session,
            "task.manage",
            operation_label="auto-level resource conflicts",
        )
        require_project_permission(
            self._user_session,
            project_id,
            "task.manage",
            operation_label="auto-level resource conflicts",
        )
        result = self._sched.auto_level_resources(
            project_id=project_id,
            max_iterations=max_iterations,
            threshold_percent=threshold_percent,
        )
        self._sched.recalculate_project_schedule(project_id)
        if emit_events and result.actions:
            domain_events.tasks_changed.emit(project_id)
        return result

    def manually_shift_task_for_leveling(
        self,
        project_id: str,
        task_id: str,
        shift_working_days: int = 1,
        reason: str = "Manual dashboard leveling",
        *,
        emit_events: bool = True,
    ) -> ResourceLevelingAction:
        require_permission(
            self._user_session,
            "task.manage",
            operation_label="manual task shift",
        )
        require_project_permission(
            self._user_session,
            project_id,
            "task.manage",
            operation_label="manual task shift",
        )
        action = self._sched.resolve_resource_conflict_manual(
            project_id=project_id,
            task_id=task_id,
            shift_working_days=shift_working_days,
            reason=reason,
        )
        self._sched.recalculate_project_schedule(project_id)
        if emit_events:
            domain_events.tasks_changed.emit(project_id)
        return action

__all__ = ["DashboardService", "DashboardData", "DashboardEVM", "UpcomingTask", "BurndownPoint"]
