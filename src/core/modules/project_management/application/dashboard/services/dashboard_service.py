"""Dashboard orchestration service — assembles all dashboard sections."""
from __future__ import annotations

from src.core.platform.contract.time_management.calendar.calendar_protocol import CalendarProtocol
from src.core.shared.events.domain_events import domain_events
from src.core.modules.project_management.access.scope_permissions import require_project_permission
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.modules.project_management.application.common.module_guard import ProjectManagementModuleGuardMixin
from src.core.modules.project_management.application.dashboard.alerts.alerts_mixin import DashboardAlertsMixin
from src.core.modules.project_management.application.dashboard.analytics.burndown import DashboardBurndownMixin
from src.core.modules.project_management.application.dashboard.analytics.evm import DashboardEvmMixin
from src.core.modules.project_management.application.dashboard.widgets.register import DashboardRegisterMixin
from src.core.modules.project_management.application.dashboard.models.dashboard_models import (
    BurndownPoint,
    DashboardData,
    DashboardEVM,
    UpcomingTask,
)
from src.core.modules.project_management.application.dashboard.reporting.portfolio import DashboardPortfolioMixin
from src.core.modules.project_management.application.dashboard.widgets.professional import DashboardProfessionalMixin
from src.core.modules.project_management.application.dashboard.widgets.upcoming import DashboardUpcomingMixin
from src.core.modules.project_management.application.resources import ResourceService
from src.core.modules.project_management.application.risk import RegisterService
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.scheduling import (
    ResourceConflict,
    ResourceLevelingAction,
    ResourceLevelingResult,
    SchedulingEngine,
)
from src.core.modules.project_management.infrastructure.reporting import ReportingService
from src.core.modules.project_management.application.tasks import TaskService
from src.core.modules.project_management.domain.tasks.hierarchy import select_leaf_tasks


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
        work_calendar_engine: CalendarProtocol,
        user_session=None,
        module_catalog_service=None,
    ):
        self._reporting: ReportingService = reporting_service
        self._tasks: TaskService = task_service
        self._projects: ProjectService = project_service
        self._resources: ResourceService = resource_service
        self._registers: RegisterService | None = register_service
        self._sched: SchedulingEngine = scheduling_engine
        self._calendar: CalendarProtocol = work_calendar_engine
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def get_dashboard_data(
        self,
        project_id: str,
        baseline_id: str | None = None,
        *,
        include_evm: bool = True,
    ) -> DashboardData:
        require_permission(self._user_session, "report.view", operation_label="view dashboard")
        require_project_permission(self._user_session, project_id, "report.view", operation_label="view dashboard")
        schedule = self._sched.recalculate_project_schedule(project_id, persist=False)
        kpi = self._reporting.get_project_kpis(project_id, schedule=schedule)
        resource_load = self._reporting.get_resource_load_summary(project_id)
        tasks = select_leaf_tasks(self._tasks.list_tasks_for_project(project_id))
        assignments = self._tasks.list_assignments_for_tasks([task.id for task in tasks])
        assignments_by_task: dict[str, list[object]] = {}
        for assignment in assignments:
            assignments_by_task.setdefault(assignment.task_id, []).append(assignment)
        resources_by_id = {
            resource.id: resource for resource in self._resources.list_resources()
        }
        owner_by_task = self._build_task_owner_map(
            tasks,
            assignments_by_task=assignments_by_task,
            resource_names={
                resource_id: resource.name
                for resource_id, resource in resources_by_id.items()
            },
        )

        alerts = self._build_alerts(project_id, kpi, resource_load, tasks=tasks)
        upcoming = self._build_upcoming_tasks(
            project_id,
            tasks=tasks,
            assignments_by_task=assignments_by_task,
            resources_by_id=resources_by_id,
        )
        burndown = self._build_burndown(project_id, kpi=kpi, tasks=tasks)
        milestones = self._build_milestone_health(
            project_id,
            schedule=schedule,
            tasks=tasks,
            owner_by_task=owner_by_task,
        )
        critical_watchlist = self._build_critical_watchlist(
            project_id,
            schedule=schedule,
            tasks=tasks,
            owner_by_task=owner_by_task,
        )
        register_snapshot = self._build_register_snapshot(project_id)
        cost_sources = self._reporting.get_project_cost_source_breakdown(project_id)
        evm_obj = (
            self._build_evm(project_id, baseline_id=baseline_id)
            if include_evm
            else None
        )

        return DashboardData(
            kpi=kpi,
            alerts=alerts,
            resource_load=resource_load,
            burndown=burndown,
            milestone_health=milestones,
            critical_watchlist=critical_watchlist,
            register_summary=(register_snapshot.summary if register_snapshot else None),
            high_risks=(list(register_snapshot.high_risks) if register_snapshot else []),
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
        require_permission(self._user_session, "task.manage", operation_label="auto-level resource conflicts")
        require_project_permission(self._user_session, project_id, "task.manage", operation_label="auto-level resource conflicts")
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
        require_permission(self._user_session, "task.manage", operation_label="manual task shift")
        require_project_permission(self._user_session, project_id, "task.manage", operation_label="manual task shift")
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


__all__ = ["DashboardService"]
