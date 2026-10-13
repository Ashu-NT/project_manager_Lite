from __future__ import annotations

from src.core.modules.project_management.application.dashboard import DashboardService
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.reporting import ReportingService
from src.core.modules.project_management.application.resources import ResourceService
from src.core.modules.project_management.application.risk import RegisterQueryHandler
from src.core.modules.project_management.application.scheduling import SchedulingEngine
from src.core.modules.project_management.application.tasks.commands.assignment import (
    TaskAssignmentCommandHandler,
)
from src.core.modules.project_management.application.tasks.queries.task_lookup import (
    TaskLookupQueryHandler,
)
from src.core.platform.infrastructure.composition.bundle import PlatformServiceBundle


def build_dashboard_service(
    platform_services: PlatformServiceBundle,
    *,
    reporting_service: ReportingService,
    task_lookup: TaskLookupQueryHandler,
    task_assignments: TaskAssignmentCommandHandler,
    project_service: ProjectService,
    resource_service: ResourceService,
    register_query: RegisterQueryHandler,
    scheduling_engine: SchedulingEngine,
) -> DashboardService:
    return DashboardService(
        reporting_service=reporting_service,
        task_lookup=task_lookup,
        task_assignments=task_assignments,
        project_service=project_service,
        resource_service=resource_service,
        register_query=register_query,
        scheduling_engine=scheduling_engine,
        work_calendar_engine=platform_services.global_calendar_shim,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
    )
