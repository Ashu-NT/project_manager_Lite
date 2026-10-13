from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.scheduling import SchedulingEngine
from src.core.modules.project_management.application.scheduling.baselines.baseline_service import (
    BaselineService,
)
from src.core.modules.project_management.application.scheduling.calendars.project_calendar_adapter import (
    ProjectCalendarAdapter,
)
from src.core.modules.project_management.infrastructure.composition.context import (
    ProjectManagementRepositoryContext,
)
from src.core.modules.project_management.infrastructure.persistence.uow.scheduling.baseline_unit_of_work import (
    SqlAlchemyBaselineUnitOfWorkFactory,
)
from src.core.platform.infrastructure.composition.bundle import PlatformServiceBundle


def build_scheduling_foundation(
    session: Session,
    repositories: ProjectManagementRepositoryContext,
    platform_services: PlatformServiceBundle,
) -> tuple[ProjectCalendarAdapter, SchedulingEngine]:
    adapter = ProjectCalendarAdapter(
        resolver=platform_services.platform_calendar_resolver,
        assignment_service=platform_services.calendar_assignment_service,
    )
    engine = SchedulingEngine(
        session,
        repositories.pm.task_repo,
        repositories.pm.dependency_repo,
        platform_services.global_calendar_shim,
        assignment_repo=repositories.pm.assignment_repo,
        resource_repo=repositories.pm.resource_repo,
        project_calendar_adapter=adapter,
    )
    return adapter, engine


def build_baseline_service(
    session: Session,
    repositories: ProjectManagementRepositoryContext,
    platform_services: PlatformServiceBundle,
    *,
    scheduling_engine: SchedulingEngine,
) -> BaselineService:
    uow_factory = SqlAlchemyBaselineUnitOfWorkFactory(
        session=session,
        transactional_dispatcher=platform_services.platform_transactional_dispatcher,
        post_commit_bus=platform_services.platform_post_commit_bus,
    )
    return BaselineService(
        session=session,
        project_repo=repositories.pm.project_repo,
        task_repo=repositories.pm.task_repo,
        planned_cost_repo=repositories.pm.planned_cost_repo,
        baseline_repo=repositories.pm.baseline_repo,
        scheduling=scheduling_engine,
        calendar=platform_services.global_calendar_shim,
        user_session=platform_services.user_session,
        activity_service=platform_services.activity_service,
        approval_service=platform_services.approval_service,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
        uow_factory=uow_factory.create,
    )
