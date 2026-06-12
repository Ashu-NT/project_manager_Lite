"""Factory for building the scheduling desktop API."""

from src.core.modules.project_management.api.desktop.scheduling.api import ProjectManagementSchedulingDesktopApi


def build_project_management_scheduling_desktop_api(
    *,
    project_service=None,
    task_service=None,
    scheduling_engine=None,
    platform_calendar_api=None,
    work_calendar_service=None,
    work_calendar_engine=None,
    baseline_service=None,
    reporting_service=None,
    change_impact_service=None,
) -> ProjectManagementSchedulingDesktopApi:
    return ProjectManagementSchedulingDesktopApi(
        project_service=project_service,
        task_service=task_service,
        scheduling_engine=scheduling_engine,
        platform_calendar_api=platform_calendar_api,
        work_calendar_service=work_calendar_service,
        work_calendar_engine=work_calendar_engine,
        baseline_service=baseline_service,
        reporting_service=reporting_service,
        change_impact_service=change_impact_service,
    )


__all__ = ["build_project_management_scheduling_desktop_api"]
