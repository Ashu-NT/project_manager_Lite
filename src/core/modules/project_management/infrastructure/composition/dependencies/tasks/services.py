from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from src.core.modules.project_management.application.resources.capacity.enterprise_resource_availability import (
    EnterpriseResourceAvailabilityService,
)
from src.core.modules.project_management.application.resources.catalog.assignment_validation import (
    AssignmentSkillValidator,
)
from src.core.modules.project_management.application.scheduling import SchedulingEngine
from src.core.modules.project_management.application.tasks import TaskService
from src.core.modules.project_management.application.timesheets import TimesheetService
from src.core.modules.project_management.infrastructure.composition.context import (
    ProjectManagementRepositoryContext,
)
from src.core.modules.project_management.infrastructure.persistence.reads.tasks import (
    SqlAlchemyTaskWorkspaceReader,
)
from src.core.modules.project_management.infrastructure.persistence.uow.tasks.task_unit_of_work import (
    SqlAlchemyTaskUnitOfWorkFactory,
)
from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)
from src.core.platform.infrastructure.composition.bundle import PlatformServiceBundle


def build_task_service(
    session: Session,
    repositories: ProjectManagementRepositoryContext,
    platform_services: PlatformServiceBundle,
    *,
    timesheet_service: TimesheetService,
    work_calendar_engine: CalendarProtocol,
    scheduling_engine: SchedulingEngine,
    assignment_skill_validator: AssignmentSkillValidator,
    enterprise_resource_availability: EnterpriseResourceAvailabilityService,
) -> TaskService:
    task_uow_factory = SqlAlchemyTaskUnitOfWorkFactory(
        session_factory=sessionmaker(bind=platform_services.session.bind, future=True),
        transactional_dispatcher=platform_services.platform_transactional_dispatcher,
        post_commit_bus=platform_services.platform_post_commit_bus,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
    )
    return TaskService(
        session,
        repositories.pm.task_repo,
        repositories.pm.dependency_repo,
        repositories.pm.assignment_repo,
        repositories.platform.time_entry_repo,
        repositories.platform.timesheet_period_repo,
        timesheet_service,
        repositories.pm.resource_repo,
        work_calendar_engine,
        scheduling_engine,
        repositories.pm.project_resource_repo,
        repositories.pm.project_repo,
        user_session=platform_services.user_session,
        activity_service=platform_services.activity_service,
        approval_service=platform_services.approval_service,
        module_catalog_service=platform_services.module_catalog_service,
        employee_repo=repositories.platform.employee_repo,
        assignment_skill_validator=assignment_skill_validator,
        tenant_context_service=platform_services.tenant_context_service,
        task_workspace_reader=SqlAlchemyTaskWorkspaceReader(session=session),
        enterprise_resource_availability_service=enterprise_resource_availability,
        task_uow_factory=task_uow_factory,
    )
