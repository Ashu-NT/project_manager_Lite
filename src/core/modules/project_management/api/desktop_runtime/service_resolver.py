from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from src.core.platform.calendar.application.calendar_protocol import CalendarProtocol
from src.core.modules.project_management.application.collaboration import (
    CollaborationService,
)
from src.core.modules.project_management.application.dashboard import DashboardService
from src.core.modules.project_management.application.financials import FinanceService
from src.core.modules.project_management.application.portfolio import PortfolioService
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.resources import (
    PortfolioResourcePoolService,
    ProjectResourceService,
    ResourceAvailabilityService,
    ResourceService,
)
from src.core.modules.project_management.application.resources.assignment_validation import (
    AssignmentSkillValidator,
)
from src.core.modules.project_management.application.resources.enterprise_resource_availability import (
    EnterpriseResourceAvailabilityService,
)
from src.core.modules.project_management.application.risk import RegisterService
from src.core.modules.project_management.application.scheduling import SchedulingEngine
from src.core.modules.project_management.application.scheduling.baselines.baseline_service import (
    BaselineService,
)
from src.core.modules.project_management.application.tasks import TaskService
from src.core.modules.project_management.application.timesheets import TimesheetService
from src.core.modules.project_management.infrastructure.reporting import ReportingService


@dataclass(frozen=True)
class ProjectManagementDesktopRuntimeServices:
    project_service: ProjectService | None
    portfolio_service: PortfolioService | None
    collaboration_service: CollaborationService | None
    register_service: RegisterService | None
    resource_service: ResourceService | None
    availability_service: (
        ResourceAvailabilityService | EnterpriseResourceAvailabilityService | None
    )
    pool_service: PortfolioResourcePoolService | None
    project_resource_service: ProjectResourceService | None
    timesheet_service: TimesheetService | None
    task_service: TaskService | None
    assignment_skill_validator: AssignmentSkillValidator | None
    scheduling_engine: SchedulingEngine | None
    work_calendar_engine: CalendarProtocol | None
    dashboard_service: DashboardService | None
    finance_service: FinanceService | None
    baseline_service: BaselineService | None
    reporting_service: ReportingService | None
    cost_service: object | None


def resolve_project_management_desktop_runtime_services(
    services: Mapping[str, object],
) -> ProjectManagementDesktopRuntimeServices:
    project_service = services.get("project_service")
    portfolio_service = services.get("portfolio_service")
    collaboration_service = services.get("collaboration_service")
    register_service = services.get("register_service")
    resource_service = services.get("resource_service")
    availability_service = services.get("resource_availability_service")
    pool_service = services.get("portfolio_resource_pool_service")
    project_resource_service = services.get("project_resource_service")
    timesheet_service = services.get("timesheet_service")
    task_service = services.get("task_service")
    assignment_skill_validator = services.get("assignment_skill_validator")
    scheduling_engine = services.get("scheduling_engine")
    work_calendar_engine = services.get("work_calendar_engine")
    dashboard_service = services.get("dashboard_service")
    finance_service = services.get("finance_service")
    baseline_service = services.get("baseline_service")
    reporting_service = services.get("reporting_service")

    if work_calendar_engine is not None and not hasattr(
        work_calendar_engine, "is_working_day"
    ):
        work_calendar_engine = None

    return ProjectManagementDesktopRuntimeServices(
        project_service=(
            project_service if isinstance(project_service, ProjectService) else None
        ),
        portfolio_service=(
            portfolio_service
            if isinstance(portfolio_service, PortfolioService)
            else None
        ),
        collaboration_service=(
            collaboration_service
            if isinstance(collaboration_service, CollaborationService)
            else None
        ),
        register_service=(
            register_service if isinstance(register_service, RegisterService) else None
        ),
        resource_service=(
            resource_service if isinstance(resource_service, ResourceService) else None
        ),
        availability_service=(
            availability_service
            if isinstance(
                availability_service,
                (
                    ResourceAvailabilityService,
                    EnterpriseResourceAvailabilityService,
                ),
            )
            else None
        ),
        pool_service=(
            pool_service
            if isinstance(pool_service, PortfolioResourcePoolService)
            else None
        ),
        project_resource_service=(
            project_resource_service
            if isinstance(project_resource_service, ProjectResourceService)
            else None
        ),
        timesheet_service=(
            timesheet_service
            if isinstance(timesheet_service, TimesheetService)
            else None
        ),
        task_service=task_service if isinstance(task_service, TaskService) else None,
        assignment_skill_validator=(
            assignment_skill_validator
            if isinstance(assignment_skill_validator, AssignmentSkillValidator)
            else None
        ),
        scheduling_engine=(
            scheduling_engine
            if isinstance(scheduling_engine, SchedulingEngine)
            else None
        ),
        work_calendar_engine=work_calendar_engine,
        dashboard_service=(
            dashboard_service
            if isinstance(dashboard_service, DashboardService)
            else None
        ),
        finance_service=(
            finance_service if isinstance(finance_service, FinanceService) else None
        ),
        baseline_service=(
            baseline_service
            if isinstance(baseline_service, BaselineService)
            else None
        ),
        reporting_service=(
            reporting_service
            if isinstance(reporting_service, ReportingService)
            else None
        ),
        cost_service=services.get("cost_service"),
    )


__all__ = [
    "ProjectManagementDesktopRuntimeServices",
    "resolve_project_management_desktop_runtime_services",
]
