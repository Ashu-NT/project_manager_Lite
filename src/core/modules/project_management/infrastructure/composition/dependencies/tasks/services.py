from __future__ import annotations

import os

from sqlalchemy.orm import Session, sessionmaker

from src.core.modules.project_management.application.resources.capacity.enterprise_resource_availability import (
    EnterpriseResourceAvailabilityService,
)
from src.core.modules.project_management.application.resources.catalog.assignment_validation import (
    AssignmentSkillValidator,
)
from src.core.modules.project_management.application.scheduling import SchedulingEngine
from src.core.modules.project_management.application.tasks import TaskService
from src.core.modules.project_management.application.tasks.commands.approved_schedule_change import (
    ApprovedScheduleChangeHandler,
)
from src.core.modules.project_management.application.tasks.commands.assignment import (
    TaskAssignmentCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.deletion import (
    TaskDeletionCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.dependency import (
    TaskDependencyCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.hierarchy import (
    TaskHierarchyCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.hierarchy_support import (
    TaskHierarchyPolicy,
)
from src.core.modules.project_management.application.tasks.commands.identity import (
    TaskCodePolicy,
)
from src.core.modules.project_management.application.tasks.commands.lifecycle import (
    TaskLifecycleCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.progress import (
    TaskProgressCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.resource_leveling_apply import (
    ResourceLevelingCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.schedule_sync import (
    TaskScheduleSynchronizer,
)
from src.core.modules.project_management.application.tasks.commands.scheduling_constraint import (
    TaskSchedulingConstraintHandler,
)
from src.core.modules.project_management.application.tasks.commands.time_entries import (
    TaskTimeEntryHandler,
)
from src.core.modules.project_management.application.tasks.commands.validation import (
    TaskValidationPolicy,
)
from src.core.modules.project_management.application.tasks.queries.dependency_diagnostics import (
    TaskDependencyDiagnosticsQueryHandler,
)
from src.core.modules.project_management.application.tasks.queries.dependency_query import (
    TaskDependencyQueryHandler,
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
from src.core.modules.project_management.application.tasks.task_unit_of_work_scope import (
    TaskUowScope,
)
from src.core.modules.project_management.application.timesheets import TimesheetService
from src.core.modules.project_management.infrastructure.composition.context import (
    ProjectManagementRepositoryContext,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.tasks.bundle import (
    TaskComposition,
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


def build_task_capabilities(
    session: Session,
    repositories: ProjectManagementRepositoryContext,
    platform_services: PlatformServiceBundle,
    *,
    timesheet_service: TimesheetService,
    work_calendar_engine: CalendarProtocol,
    scheduling_engine: SchedulingEngine,
    assignment_skill_validator: AssignmentSkillValidator,
    enterprise_resource_availability: EnterpriseResourceAvailabilityService,
) -> TaskComposition:
    task_uow_factory = SqlAlchemyTaskUnitOfWorkFactory(
        session_factory=sessionmaker(bind=platform_services.session.bind, future=True),
        transactional_dispatcher=platform_services.platform_transactional_dispatcher,
        post_commit_bus=platform_services.platform_post_commit_bus,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
    )
    task_uow_scope = TaskUowScope(
        factory=task_uow_factory,
        tasks=repositories.pm.task_repo,
        assignments=repositories.pm.assignment_repo,
        dependencies=repositories.pm.dependency_repo,
        project_resources=repositories.pm.project_resource_repo,
        time_entries=repositories.platform.time_entry_repo,
        enterprise_audit_service=None,
        activity_service=platform_services.activity_service,
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
    hierarchy_policy = TaskHierarchyPolicy(
        task_repo=repositories.pm.task_repo,
        assignment_repo=repositories.pm.assignment_repo,
        dependency_repo=repositories.pm.dependency_repo,
    )
    validation_policy = TaskValidationPolicy(
        task_repo=repositories.pm.task_repo,
        assignment_repo=repositories.pm.assignment_repo,
        resource_repo=repositories.pm.resource_repo,
        project_repo=repositories.pm.project_repo,
        availability_service=enterprise_resource_availability,
    )
    schedule_synchronizer = TaskScheduleSynchronizer(
        scheduling_engine=scheduling_engine,
        task_repo=repositories.pm.task_repo,
    )
    code_policy = TaskCodePolicy(task_repo=repositories.pm.task_repo)
    scheduling_constraint_handler = TaskSchedulingConstraintHandler(
        task_repo=repositories.pm.task_repo,
        user_session=platform_services.user_session,
        approval_service=platform_services.approval_service,
        tenant_context_service=platform_services.tenant_context_service,
        scheduling_engine=scheduling_engine,
        work_calendar_engine=work_calendar_engine,
        schedule_synchronizer=schedule_synchronizer,
        uow_scope=task_uow_scope,
    )
    lifecycle_handler = TaskLifecycleCommandHandler(
        task_repo=repositories.pm.task_repo,
        work_calendar_engine=work_calendar_engine,
        user_session=platform_services.user_session,
        tenant_context_service=platform_services.tenant_context_service,
        code_policy=code_policy,
        hierarchy_policy=hierarchy_policy,
        validation_policy=validation_policy,
        scheduling_constraint_handler=scheduling_constraint_handler,
        uow_scope=task_uow_scope,
    )
    hierarchy_command_handler = TaskHierarchyCommandHandler(
        task_repo=repositories.pm.task_repo,
        user_session=platform_services.user_session,
        tenant_context_service=platform_services.tenant_context_service,
        hierarchy_policy=hierarchy_policy,
        uow_scope=task_uow_scope,
    )
    progress_handler = TaskProgressCommandHandler(
        task_repo=repositories.pm.task_repo,
        user_session=platform_services.user_session,
        tenant_context_service=platform_services.tenant_context_service,
        hierarchy_policy=hierarchy_policy,
        validation_policy=validation_policy,
        uow_scope=task_uow_scope,
    )
    dependency_diagnostics_handler = TaskDependencyDiagnosticsQueryHandler(
        task_repo=repositories.pm.task_repo,
        dependency_repo=repositories.pm.dependency_repo,
        work_calendar_engine=work_calendar_engine,
        scheduling_engine=scheduling_engine,
        user_session=platform_services.user_session,
    )
    overallocation_policy = os.getenv("PM_OVERALLOCATION_POLICY", "warn").strip().lower()
    assignment_handler = TaskAssignmentCommandHandler(
        task_repo=repositories.pm.task_repo,
        assignment_repo=repositories.pm.assignment_repo,
        resource_repo=repositories.pm.resource_repo,
        project_resource_repo=repositories.pm.project_resource_repo,
        time_entry_repo=repositories.platform.time_entry_repo,
        employee_repo=repositories.platform.employee_repo,
        user_session=platform_services.user_session,
        tenant_context_service=platform_services.tenant_context_service,
        hierarchy_policy=hierarchy_policy,
        validation_policy=validation_policy,
        assignment_skill_validator=assignment_skill_validator,
        enterprise_resource_availability_service=enterprise_resource_availability,
        uow_scope=task_uow_scope,
        overallocation_policy="strict" if overallocation_policy == "strict" else "warn",
    )
    service = TaskService(
        session,
        repositories.pm.task_repo,
        repositories.pm.dependency_repo,
        repositories.pm.assignment_repo,
        scheduling_engine,
        user_session=platform_services.user_session,
        activity_service=platform_services.activity_service,
        approval_service=platform_services.approval_service,
        module_catalog_service=platform_services.module_catalog_service,
        task_uow_scope=task_uow_scope,
        deletion_handler=TaskDeletionCommandHandler(
            task_repo=repositories.pm.task_repo,
            user_session=platform_services.user_session,
            tenant_context_service=platform_services.tenant_context_service,
            uow_scope=task_uow_scope,
        ),
        progress_handler=progress_handler,
        time_entry_handler=TaskTimeEntryHandler(
            timesheet_service=timesheet_service,
            task_repo=repositories.pm.task_repo,
            assignment_repo=repositories.pm.assignment_repo,
            user_session=platform_services.user_session,
        ),
        approved_schedule_change_handler=ApprovedScheduleChangeHandler(
            task_repo=repositories.pm.task_repo,
            tenant_context_service=platform_services.tenant_context_service,
            work_calendar_engine=work_calendar_engine,
            scheduling_engine=scheduling_engine,
            schedule_synchronizer=schedule_synchronizer,
            validation_policy=validation_policy,
            uow_scope=task_uow_scope,
        ),
        hierarchy_command_handler=hierarchy_command_handler,
        scheduling_constraint_handler=scheduling_constraint_handler,
        lifecycle_handler=lifecycle_handler,
        dependency_command_handler=TaskDependencyCommandHandler(
            task_repo=repositories.pm.task_repo,
            dependency_repo=repositories.pm.dependency_repo,
            user_session=platform_services.user_session,
            approval_service=platform_services.approval_service,
            tenant_context_service=platform_services.tenant_context_service,
            hierarchy_policy=hierarchy_policy,
            diagnostics_handler=dependency_diagnostics_handler,
            schedule_synchronizer=schedule_synchronizer,
            uow_scope=task_uow_scope,
        ),
        dependency_query_handler=TaskDependencyQueryHandler(
            task_repo=repositories.pm.task_repo,
            dependency_repo=repositories.pm.dependency_repo,
            user_session=platform_services.user_session,
        ),
        assignment_handler=assignment_handler,
        resource_leveling_handler=ResourceLevelingCommandHandler(
            task_repo=repositories.pm.task_repo,
            assignment_repo=repositories.pm.assignment_repo,
            dependency_repo=repositories.pm.dependency_repo,
            resource_repo=repositories.pm.resource_repo,
            work_calendar_engine=work_calendar_engine,
            user_session=platform_services.user_session,
            approval_service=platform_services.approval_service,
            tenant_context_service=platform_services.tenant_context_service,
            schedule_synchronizer=schedule_synchronizer,
            uow_scope=task_uow_scope,
        ),
        detail_query_handler=detail_query_handler,
        lookup_query_handler=lookup_query_handler,
        hierarchy_query_handler=TaskHierarchyQueryHandler(
            task_repo=repositories.pm.task_repo,
            work_calendar_engine=work_calendar_engine,
            user_session=platform_services.user_session,
        ),
    )
    return TaskComposition(
        service=service,
        lookup=lookup_query_handler,
        workspace=workspace_query_handler,
        detail=detail_query_handler,
        dependency_diagnostics=dependency_diagnostics_handler,
        assignment=assignment_handler,
        lifecycle=lifecycle_handler,
        hierarchy=hierarchy_command_handler,
        progress=progress_handler,
    )
