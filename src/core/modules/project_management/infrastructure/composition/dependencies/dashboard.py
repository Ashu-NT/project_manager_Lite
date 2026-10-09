from __future__ import annotations

from src.core.modules.project_management.application.dashboard import DashboardService
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.reporting import ReportingService
from src.core.modules.project_management.application.resources import ResourceService
from src.core.modules.project_management.application.risk import RegisterService
from src.core.modules.project_management.application.scheduling import SchedulingEngine
from src.core.modules.project_management.application.tasks import TaskService
from src.infra.composition.modules.platform_registry import PlatformServiceBundle


def build_dashboard_service(
    platform_services: PlatformServiceBundle,
    *,
    reporting_service: ReportingService,
    task_service: TaskService,
    project_service: ProjectService,
    resource_service: ResourceService,
    register_service: RegisterService,
    scheduling_engine: SchedulingEngine,
) -> DashboardService:
    return DashboardService(
        reporting_service=reporting_service,
        task_service=task_service,
        project_service=project_service,
        resource_service=resource_service,
        register_service=register_service,
        scheduling_engine=scheduling_engine,
        work_calendar_engine=platform_services.global_calendar_shim,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
    )
