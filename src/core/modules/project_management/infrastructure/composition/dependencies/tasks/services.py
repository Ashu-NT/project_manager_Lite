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
from src.core.modules.project_management.application.tasks.commands.identity import (
    TaskCodePolicy,
)
from src.core.modules.project_management.application.tasks.commands.schedule_sync import (
    TaskScheduleSynchronizer,
)
from src.core.modules.project_management.application.tasks.commands.validation import (
    TaskValidationPolicy,
)
from src.core.modules.project_management.application.tasks.queries.dependency_diagnostics import (
    TaskDependencyDiagnosticsQueryHandler,
)
from src.core.modules.project_management.application.tasks.queries.hierarchy_query import (
    TaskHierarchyQueryHandler,
)
from src.core.modules.project_management.application.tasks.queries.task_detail_page import (
    TaskDetailPageQueryHandler,
)
from src.core.modules.project_management.application.tasks.queries.task_lookup import (
    TaskLookupQueryHandler,
)
from src.core.modules.project_management.application.tasks.queries.task_workspace_page import (
    TaskWorkspacePageQueryHandler,
)
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
    task_workspace_reader = SqlAlchemyTaskWorkspaceReader(session=session)
    detail_query_handler = TaskDetailPageQueryHandler(
        task_repo=repositories.pm.task_repo,
        task_workspace_reader=task_workspace_reader,
        user_session=platform_services.user_session,
        tenant_context_service=platform_services.tenant_context_service,
    )
    workspace_query_handler = TaskWorkspacePageQueryHandler(
        task_workspace_reader=task_workspace_reader,
        work_calendar_engine=work_calendar_engine,
        user_session=platform_services.user_session,
        tenant_context_service=platform_services.tenant_context_service,
    )
    lookup_query_handler = TaskLookupQueryHandler(
        task_repo=repositories.pm.task_repo,
        assignment_repo=repositories.pm.assignment_repo,
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
        task_workspace_reader=task_workspace_reader,
        enterprise_resource_availability_service=enterprise_resource_availability,
        task_uow_factory=task_uow_factory,
        detail_query_handler=detail_query_handler,
        workspace_query_handler=workspace_query_handler,
        lookup_query_handler=lookup_query_handler,
        hierarchy_query_handler=TaskHierarchyQueryHandler(
            task_repo=repositories.pm.task_repo,
            work_calendar_engine=work_calendar_engine,
            user_session=platform_services.user_session,
        ),
        dependency_diagnostics_handler=TaskDependencyDiagnosticsQueryHandler(
            task_repo=repositories.pm.task_repo,
            dependency_repo=repositories.pm.dependency_repo,
            work_calendar_engine=work_calendar_engine,
            scheduling_engine=scheduling_engine,
            user_session=platform_services.user_session,
        ),
        code_policy=TaskCodePolicy(task_repo=repositories.pm.task_repo),
        validation_policy=TaskValidationPolicy(
            task_repo=repositories.pm.task_repo,
            assignment_repo=repositories.pm.assignment_repo,
            resource_repo=repositories.pm.resource_repo,
            project_repo=repositories.pm.project_repo,
            availability_service=enterprise_resource_availability,
        ),
        schedule_synchronizer=TaskScheduleSynchronizer(
            scheduling_engine=scheduling_engine,
            task_repo=repositories.pm.task_repo,
        ),
    )
