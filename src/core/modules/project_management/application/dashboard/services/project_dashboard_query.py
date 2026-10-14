"""Project dashboard orchestration -- assembles every widget for one project."""
from __future__ import annotations

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.dashboard.alerts.alert_builder import (
    DashboardAlertBuilder,
)
from src.core.modules.project_management.application.dashboard.analytics.burndown import (
    DashboardBurndownBuilder,
)
from src.core.modules.project_management.application.dashboard.analytics.evm import (
    DashboardEvmWidget,
)
from src.core.modules.project_management.application.dashboard.models.dashboard_models import (
    DashboardData,
)
from src.core.modules.project_management.application.dashboard.widgets.professional import (
    DashboardScheduleHealthWidget,
)
from src.core.modules.project_management.application.dashboard.widgets.register import (
    DashboardRegisterWidget,
)
from src.core.modules.project_management.application.dashboard.widgets.upcoming import (
    DashboardUpcomingWidget,
)
from src.core.modules.project_management.contracts.ports.dashboard.dashboard_queries import (
    DashboardCostSourceQuery,
    DashboardKpiQuery,
    DashboardResourceQuery,
    DashboardScheduleQuery,
    DashboardTaskQuery,
)
from src.core.modules.project_management.domain.tasks.hierarchy import select_leaf_tasks
from src.core.modules.project_management.domain.tasks.task import TaskAssignment
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)


class ProjectDashboardQueryHandler(ProjectManagementModuleGuardMixin):
    """Loads project read data once, then feeds each dashboard widget."""

    def __init__(
        self,
        *,
        kpi_report: DashboardKpiQuery,
        cost_sources: DashboardCostSourceQuery,
        evm_widget: DashboardEvmWidget,
        register_widget: DashboardRegisterWidget,
        task_lookup: DashboardTaskQuery,
        resource_query: DashboardResourceQuery,
        scheduling_engine: DashboardScheduleQuery,
        user_session=None,
        module_catalog_service=None,
    ) -> None:
        self._kpi_report = kpi_report
        self._cost_sources = cost_sources
        self._evm = evm_widget
        self._registers = register_widget
        self._task_lookup = task_lookup
        self._resources = resource_query
        self._sched = scheduling_engine
        self._alerts = DashboardAlertBuilder()
        self._burndown = DashboardBurndownBuilder()
        self._upcoming = DashboardUpcomingWidget()
        self._schedule_health = DashboardScheduleHealthWidget()
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
        kpi = self._kpi_report.get_project_kpis(project_id, schedule=schedule)
        resource_load = self._kpi_report.get_resource_load_summary(project_id)
        tasks = select_leaf_tasks(self._task_lookup.list_tasks_for_project(project_id))
        assignments = self._task_lookup.list_assignments_for_tasks([task.id for task in tasks])
        assignments_by_task: dict[str, list[TaskAssignment]] = {}
        for assignment in assignments:
            assignments_by_task.setdefault(assignment.task_id, []).append(assignment)
        resources_by_id = {
            resource.id: resource for resource in self._resources.list_resources()
        }
        owner_by_task = self._schedule_health.build_task_owner_map(
            tasks,
            assignments_by_task=assignments_by_task,
            resource_names={
                resource_id: resource.name
                for resource_id, resource in resources_by_id.items()
            },
        )

        alerts = self._alerts.build(kpi, resource_load, tasks=tasks)
        upcoming = self._upcoming.build(
            tasks=tasks,
            assignments_by_task=assignments_by_task,
            resources_by_id=resources_by_id,
        )
        burndown = self._burndown.build(kpi=kpi, tasks=tasks)
        milestones = self._schedule_health.build_milestone_health(
            schedule=schedule,
            tasks=tasks,
            owner_by_task=owner_by_task,
        )
        critical_watchlist = self._schedule_health.build_critical_watchlist(
            schedule=schedule,
            tasks=tasks,
            owner_by_task=owner_by_task,
        )
        register_snapshot = self._registers.build_snapshot(project_id)
        # Cost source breakdown is Project Finance authority data; report.view
        # (checked above) is not sufficient on its own -- finance.read governs
        # it, matching FinanceService's own read authority. Redact rather than
        # fail the whole dashboard so non-financial dashboard widgets still work.
        can_read_finance = bool(
            self._user_session is not None
            and self._user_session.has_project_permission(project_id, "finance.read")
        )
        cost_sources = (
            self._cost_sources.get_project_cost_source_breakdown(project_id)
            if can_read_finance
            else None
        )
        evm_obj = (
            self._evm.build(project_id, baseline_id=baseline_id)
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


__all__ = ["ProjectDashboardQueryHandler"]
