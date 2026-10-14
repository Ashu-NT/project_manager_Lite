from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.application.dashboard import (
    PortfolioDashboardQueryHandler,
    ProjectDashboardQueryHandler,
)
from src.core.modules.project_management.application.dashboard.analytics.evm import (
    DashboardEvmWidget,
)
from src.core.modules.project_management.application.dashboard.widgets.register import (
    DashboardRegisterWidget,
)
from src.core.modules.project_management.application.projects.queries.project_query import (
    ProjectQueryHandler,
)
from src.core.modules.project_management.application.resources import (
    ResourceQueryHandler,
)
from src.core.modules.project_management.application.risk import RegisterQueryHandler
from src.core.modules.project_management.application.scheduling import SchedulingEngine
from src.core.modules.project_management.application.tasks.queries.task_lookup import (
    TaskLookupQueryHandler,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.reporting.bundle import (
    ReportingComposition,
)
from src.core.platform.infrastructure.composition.bundle import PlatformServiceBundle


@dataclass(frozen=True)
class DashboardComposition:
    project: ProjectDashboardQueryHandler
    portfolio: PortfolioDashboardQueryHandler


def build_dashboard_capabilities(
    platform_services: PlatformServiceBundle,
    *,
    reporting: ReportingComposition,
    task_lookup: TaskLookupQueryHandler,
    project_query: ProjectQueryHandler,
    resource_query: ResourceQueryHandler,
    register_query: RegisterQueryHandler,
    scheduling_engine: SchedulingEngine,
) -> DashboardComposition:
    return DashboardComposition(
        project=ProjectDashboardQueryHandler(
            kpi_report=reporting.kpi,
            cost_sources=reporting.cost_breakdown,
            evm_widget=DashboardEvmWidget(reporting.earned_value),
            register_widget=DashboardRegisterWidget(register_query),
            task_lookup=task_lookup,
            resource_query=resource_query,
            scheduling_engine=scheduling_engine,
            user_session=platform_services.user_session,
            module_catalog_service=platform_services.module_catalog_service,
        ),
        portfolio=PortfolioDashboardQueryHandler(
            kpi_report=reporting.kpi,
            project_query=project_query,
            resource_query=resource_query,
            task_lookup=task_lookup,
            scheduling_engine=scheduling_engine,
            work_calendar_engine=platform_services.global_calendar_shim,
            user_session=platform_services.user_session,
            module_catalog_service=platform_services.module_catalog_service,
        ),
    )
