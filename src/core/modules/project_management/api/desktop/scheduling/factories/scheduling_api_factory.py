"""Factory for building the scheduling desktop API."""

from src.core.modules.project_management.api.desktop.scheduling.api import (
    ProjectManagementSchedulingDesktopApi,
)


def build_project_management_scheduling_desktop_api(
    *,
    project_service=None,
    task_lookup_query=None,
    task_detail_query=None,
    task_hierarchy_query=None,
    task_dependency_query=None,
    task_dependency_commands=None,
    task_leveling_commands=None,
    scheduling_engine=None,
    platform_calendar_api=None,
    work_calendar_service=None,
    work_calendar_engine=None,
    baseline_query=None,
    baseline_commands=None,
    baseline_compare_report=None,
    project_kpi_report=None,
    change_impact_service=None,
    constraint_validator=None,
    tenant_context_service=None,
) -> ProjectManagementSchedulingDesktopApi:
    return ProjectManagementSchedulingDesktopApi(
        project_service=project_service,
        task_lookup_query=task_lookup_query,
        task_detail_query=task_detail_query,
        task_hierarchy_query=task_hierarchy_query,
        task_dependency_query=task_dependency_query,
        task_dependency_commands=task_dependency_commands,
        task_leveling_commands=task_leveling_commands,
        scheduling_engine=scheduling_engine,
        platform_calendar_api=platform_calendar_api,
        work_calendar_service=work_calendar_service,
        work_calendar_engine=work_calendar_engine,
        baseline_query=baseline_query,
        baseline_commands=baseline_commands,
        baseline_compare_report=baseline_compare_report,
        project_kpi_report=project_kpi_report,
        change_impact_service=change_impact_service,
        constraint_validator=constraint_validator,
        tenant_context_service=tenant_context_service,
    )


__all__ = ["build_project_management_scheduling_desktop_api"]
