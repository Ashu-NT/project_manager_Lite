from __future__ import annotations

from collections.abc import Mapping

from src.core.modules.inventory_procurement import ProcurementService, ReservationService
from src.core.modules.project_management.api.desktop import (
    build_project_management_collaboration_desktop_api,
    build_project_management_dashboard_desktop_api,
    build_project_management_financials_desktop_api,
    build_project_management_portfolio_desktop_api,
    build_project_management_projects_desktop_api,
    build_project_management_register_desktop_api,
    build_project_management_resources_desktop_api,
    build_project_management_scheduling_desktop_api,
    build_project_management_tasks_desktop_api,
    build_project_management_timesheets_desktop_api,
)

from src.core.modules.project_management.api.desktop_runtime.registry import (
    ProjectManagementDesktopRuntimeApis,
    ProjectManagementDesktopRuntimePlatformDependencies,
)
from src.core.modules.project_management.api.desktop_runtime.scheduling_helpers import (
    build_schedule_change_impact_service,
)
from src.core.modules.project_management.api.desktop_runtime.service_resolver import (
    resolve_project_management_desktop_runtime_services,
)


def build_project_management_desktop_runtime_apis(
    services: Mapping[str, object],
    platform_dependencies: ProjectManagementDesktopRuntimePlatformDependencies,
) -> ProjectManagementDesktopRuntimeApis:
    resolved = resolve_project_management_desktop_runtime_services(services)
    register_desktop_api = build_project_management_register_desktop_api(
        project_service=resolved.project_service,
        register_service=resolved.register_service,
    )
    procurement_service = (
        platform_dependencies.procurement_service
        if isinstance(platform_dependencies.procurement_service, ProcurementService)
        else None
    )
    reservation_service = (
        platform_dependencies.reservation_service
        if isinstance(platform_dependencies.reservation_service, ReservationService)
        else None
    )
    change_impact_service = build_schedule_change_impact_service(
        resolved.task_service,
        resolved.work_calendar_engine,
    )
    return ProjectManagementDesktopRuntimeApis(
        project_management_dashboard=build_project_management_dashboard_desktop_api(
            project_service=resolved.project_service,
            dashboard_service=resolved.dashboard_service,
            baseline_service=resolved.baseline_service,
            reporting_service=resolved.reporting_service,
            register_service=resolved.register_service,
            collaboration_service=resolved.collaboration_service,
            approval_service=platform_dependencies.approval_service,
        ),
        project_management_collaboration=build_project_management_collaboration_desktop_api(
            collaboration_service=resolved.collaboration_service,
        ),
        project_management_financials=build_project_management_financials_desktop_api(
            project_service=resolved.project_service,
            task_service=resolved.task_service,
            cost_service=(
                resolved.cost_service
                if hasattr(resolved.cost_service, "list_cost_items_for_project")
                else None
            ),
            finance_service=resolved.finance_service,
            procurement_service=procurement_service,
            baseline_service=resolved.baseline_service,
        ),
        project_management_portfolio=build_project_management_portfolio_desktop_api(
            project_service=resolved.project_service,
            portfolio_service=resolved.portfolio_service,
            pool_service=resolved.pool_service,
        ),
        project_management_projects=build_project_management_projects_desktop_api(
            project_service=resolved.project_service,
            project_resource_service=resolved.project_resource_service,
            resource_service=resolved.resource_service,
            site_service=platform_dependencies.site_service,
        ),
        project_management_register=register_desktop_api,
        project_management_risk=register_desktop_api,
        project_management_resources=build_project_management_resources_desktop_api(
            resource_service=resolved.resource_service,
            employee_service=platform_dependencies.employee_service,
            availability_service=resolved.availability_service,
            task_service=resolved.task_service,
            assignment_repo=getattr(resolved.task_service, "_assignment_repo", None),
            project_service=resolved.project_service,
            work_calendar_engine=resolved.work_calendar_engine,
        ),
        project_management_scheduling=build_project_management_scheduling_desktop_api(
            project_service=resolved.project_service,
            task_service=resolved.task_service,
            scheduling_engine=resolved.scheduling_engine,
            platform_calendar_api=None,
            work_calendar_service=None,
            work_calendar_engine=resolved.work_calendar_engine,
            baseline_service=resolved.baseline_service,
            reporting_service=resolved.reporting_service,
            change_impact_service=change_impact_service,
        ),
        project_management_tasks=build_project_management_tasks_desktop_api(
            project_service=resolved.project_service,
            task_service=resolved.task_service,
            project_resource_service=resolved.project_resource_service,
            resource_service=resolved.resource_service,
            reservation_service=reservation_service,
            assignment_skill_validator=resolved.assignment_skill_validator,
            schedule_change_impact_service=change_impact_service,
        ),
        project_management_timesheets=build_project_management_timesheets_desktop_api(
            project_service=resolved.project_service,
            task_service=resolved.task_service,
            resource_service=resolved.resource_service,
            timesheet_service=resolved.timesheet_service,
        ),
    )


__all__ = ["build_project_management_desktop_runtime_apis"]
