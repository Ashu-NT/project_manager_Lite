from __future__ import annotations

from collections.abc import Mapping

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
from src.core.modules.project_management.application.scheduling.cpm.constraint_validator import (
    ConstraintValidator,
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
    change_impact_service = build_schedule_change_impact_service(
        resolved.task_service,
        resolved.work_calendar_engine,
        resolved.baseline_service,
    )
    constraint_validator = (
        ConstraintValidator(resolved.work_calendar_engine)
        if resolved.work_calendar_engine is not None
        else None
    )
    return ProjectManagementDesktopRuntimeApis(
        project_management_dashboard=build_project_management_dashboard_desktop_api(
            project_service=resolved.project_service,
            dashboard_service=resolved.dashboard_service,
            baseline_service=resolved.baseline_service,
            reporting_service=resolved.reporting_service,
            collaboration_service=resolved.collaboration_service,
            approval_service=platform_dependencies.approval_service,
            task_service=resolved.task_service,
        ),
        project_management_collaboration=build_project_management_collaboration_desktop_api(
            collaboration_service=resolved.collaboration_service,
        ),
        project_management_financials=build_project_management_financials_desktop_api(
            project_service=resolved.project_service,
            task_service=resolved.task_service,
            finance_service=resolved.finance_service,
            baseline_service=resolved.baseline_service,
            finance_workspace_query=resolved.finance_workspace_query,
            financial_configuration_service=resolved.financial_configuration_service,
            cost_entry_service=resolved.cost_entry_service,
            commitment_service=resolved.commitment_service,
            forecast_version_service=resolved.forecast_version_service,
            financial_change_service=resolved.financial_change_service,
            billing_profile_service=resolved.billing_profile_service,
            billing_preparation_service=resolved.billing_preparation_service,
            reporting_service=resolved.reporting_service,
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
            department_service=platform_dependencies.department_service,
        ),
        project_management_register=register_desktop_api,
        project_management_risk=register_desktop_api,
        project_management_resources=build_project_management_resources_desktop_api(
            resource_service=resolved.resource_service,
            employee_service=platform_dependencies.employee_service,
            availability_service=resolved.resource_multi_project_allocation_service,
            task_service=resolved.task_service,
            project_service=resolved.project_service,
            department_service=platform_dependencies.department_service,
            site_service=platform_dependencies.site_service,
        ),
        project_management_scheduling=build_project_management_scheduling_desktop_api(
            project_service=resolved.project_service,
            task_service=resolved.task_service,
            scheduling_engine=resolved.scheduling_engine,
            platform_calendar_api=platform_dependencies.enterprise_calendar_api,
            work_calendar_service=None,
            work_calendar_engine=resolved.work_calendar_engine,
            baseline_service=resolved.baseline_service,
            reporting_service=resolved.reporting_service,
            change_impact_service=change_impact_service,
            constraint_validator=constraint_validator,
            tenant_context_service=resolved.tenant_context_service,
        ),
        project_management_tasks=build_project_management_tasks_desktop_api(
            project_service=resolved.project_service,
            task_service=resolved.task_service,
            project_resource_service=resolved.project_resource_service,
            resource_service=resolved.resource_service,
            reservation_service=platform_dependencies.reservation_service,
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
