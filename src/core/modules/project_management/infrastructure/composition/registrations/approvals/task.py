from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.scheduling import (
    ProjectCalendarAdapter,
    SchedulingEngine,
)
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
from src.core.modules.project_management.application.tasks.service import TaskService
from src.core.modules.project_management.application.tasks.task_unit_of_work_scope import (
    TaskUowScope,
)
from src.core.modules.project_management.infrastructure.approval.task_apply_participant import (
    TaskApprovalDeps,
)
from src.core.modules.project_management.infrastructure.composition.registrations.approvals._shared import (
    build_approval_repository_context,
    wire_tenant_context_service,
)
from src.core.platform.application.history.activity.activity_service import (
    ActivityService,
)
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)


def build_task_approval_deps(
    session: Session,
    *,
    user_session,
    tenant_context_service,
    work_calendar_engine: CalendarProtocol,
    platform_calendar_resolver,
    calendar_assignment_service,
    module_catalog_service=None,
) -> TaskApprovalDeps:

    bundle = build_approval_repository_context(session, tenant_context_service)

    for field_name in bundle.pm.__dataclass_fields__:
        wire_tenant_context_service(getattr(bundle.pm, field_name), tenant_context_service)

    activity_service = ActivityService(
        session=session,
        activity_repo=bundle.platform.activity_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
    enterprise_audit_service = EnterpriseAuditService(
        session=session,
        audit_repo=bundle.platform.audit_entry_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
    project_calendar_adapter = ProjectCalendarAdapter(
        resolver=platform_calendar_resolver,
        assignment_service=calendar_assignment_service,
    )
    scheduling_engine = SchedulingEngine(
        session,
        bundle.pm.task_repo,
        bundle.pm.dependency_repo,
        work_calendar_engine,
        assignment_repo=bundle.pm.assignment_repo,
        resource_repo=bundle.pm.resource_repo,
        project_calendar_adapter=project_calendar_adapter,
    )
    task_uow_scope = TaskUowScope(
        factory=None,
        tasks=bundle.pm.task_repo,
        assignments=bundle.pm.assignment_repo,
        dependencies=bundle.pm.dependency_repo,
        project_resources=bundle.pm.project_resource_repo,
        time_entries=bundle.platform.time_entry_repo,
        enterprise_audit_service=enterprise_audit_service,
        activity_service=activity_service,
    )
    hierarchy_policy = TaskHierarchyPolicy(
        task_repo=bundle.pm.task_repo,
        assignment_repo=bundle.pm.assignment_repo,
        dependency_repo=bundle.pm.dependency_repo,
    )
    validation_policy = TaskValidationPolicy(
        task_repo=bundle.pm.task_repo,
        assignment_repo=bundle.pm.assignment_repo,
        resource_repo=bundle.pm.resource_repo,
        project_repo=bundle.pm.project_repo,
        availability_service=None,
    )
    schedule_synchronizer = TaskScheduleSynchronizer(
        scheduling_engine=scheduling_engine,
        task_repo=bundle.pm.task_repo,
    )
    code_policy = TaskCodePolicy(task_repo=bundle.pm.task_repo)
    scheduling_constraint_handler = TaskSchedulingConstraintHandler(
        task_repo=bundle.pm.task_repo,
        user_session=user_session,
        approval_service=None,
        tenant_context_service=tenant_context_service,
        scheduling_engine=scheduling_engine,
        work_calendar_engine=work_calendar_engine,
        schedule_synchronizer=schedule_synchronizer,
        uow_scope=task_uow_scope,
    )
    lifecycle_handler = TaskLifecycleCommandHandler(
        task_repo=bundle.pm.task_repo,
        work_calendar_engine=work_calendar_engine,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        code_policy=code_policy,
        hierarchy_policy=hierarchy_policy,
        validation_policy=validation_policy,
        scheduling_constraint_handler=scheduling_constraint_handler,
        uow_scope=task_uow_scope,
    )
    dependency_diagnostics_handler = TaskDependencyDiagnosticsQueryHandler(
        task_repo=bundle.pm.task_repo,
        dependency_repo=bundle.pm.dependency_repo,
        work_calendar_engine=work_calendar_engine,
        scheduling_engine=scheduling_engine,
        user_session=user_session,
    )
    task_service = TaskService(
        session,
        bundle.pm.task_repo,
        bundle.pm.dependency_repo,
        bundle.pm.assignment_repo,
        scheduling_engine,
        user_session=user_session,
        activity_service=activity_service,
        approval_service=None,
        module_catalog_service=module_catalog_service,
        enterprise_audit_service=enterprise_audit_service,
        task_uow_scope=task_uow_scope,
        deletion_handler=TaskDeletionCommandHandler(
            task_repo=bundle.pm.task_repo,
            user_session=user_session,
            tenant_context_service=tenant_context_service,
            uow_scope=task_uow_scope,
        ),
        progress_handler=TaskProgressCommandHandler(
            task_repo=bundle.pm.task_repo,
            user_session=user_session,
            tenant_context_service=tenant_context_service,
            hierarchy_policy=hierarchy_policy,
            validation_policy=validation_policy,
            uow_scope=task_uow_scope,
        ),
        time_entry_handler=TaskTimeEntryHandler(
            timesheet_service=None,
            task_repo=bundle.pm.task_repo,
            assignment_repo=bundle.pm.assignment_repo,
            user_session=user_session,
        ),
        approved_schedule_change_handler=ApprovedScheduleChangeHandler(
            task_repo=bundle.pm.task_repo,
            tenant_context_service=tenant_context_service,
            work_calendar_engine=work_calendar_engine,
            scheduling_engine=scheduling_engine,
            schedule_synchronizer=schedule_synchronizer,
            validation_policy=validation_policy,
            uow_scope=task_uow_scope,
        ),
        hierarchy_command_handler=TaskHierarchyCommandHandler(
            task_repo=bundle.pm.task_repo,
            user_session=user_session,
            tenant_context_service=tenant_context_service,
            hierarchy_policy=hierarchy_policy,
            uow_scope=task_uow_scope,
        ),
        scheduling_constraint_handler=scheduling_constraint_handler,
        lifecycle_handler=lifecycle_handler,
        dependency_command_handler=TaskDependencyCommandHandler(
            task_repo=bundle.pm.task_repo,
            dependency_repo=bundle.pm.dependency_repo,
            user_session=user_session,
            approval_service=None,
            tenant_context_service=tenant_context_service,
            hierarchy_policy=hierarchy_policy,
            diagnostics_handler=dependency_diagnostics_handler,
            schedule_synchronizer=schedule_synchronizer,
            uow_scope=task_uow_scope,
        ),
        dependency_query_handler=TaskDependencyQueryHandler(
            task_repo=bundle.pm.task_repo,
            dependency_repo=bundle.pm.dependency_repo,
            user_session=user_session,
        ),
        assignment_handler=TaskAssignmentCommandHandler(
            task_repo=bundle.pm.task_repo,
            assignment_repo=bundle.pm.assignment_repo,
            resource_repo=bundle.pm.resource_repo,
            project_resource_repo=bundle.pm.project_resource_repo,
            time_entry_repo=bundle.platform.time_entry_repo,
            employee_repo=bundle.platform.employee_repo,
            user_session=user_session,
            tenant_context_service=tenant_context_service,
            hierarchy_policy=hierarchy_policy,
            validation_policy=validation_policy,
            assignment_skill_validator=None,
            enterprise_resource_availability_service=None,
            uow_scope=task_uow_scope,
            overallocation_policy="warn",
        ),
        resource_leveling_handler=ResourceLevelingCommandHandler(
            task_repo=bundle.pm.task_repo,
            assignment_repo=bundle.pm.assignment_repo,
            dependency_repo=bundle.pm.dependency_repo,
            resource_repo=bundle.pm.resource_repo,
            work_calendar_engine=work_calendar_engine,
            user_session=user_session,
            approval_service=None,
            tenant_context_service=tenant_context_service,
            schedule_synchronizer=schedule_synchronizer,
            uow_scope=task_uow_scope,
        ),
        detail_query_handler=TaskDetailPageQueryHandler(
            task_repo=bundle.pm.task_repo,
            task_workspace_reader=None,
            user_session=user_session,
            tenant_context_service=tenant_context_service,
        ),
        lookup_query_handler=TaskLookupQueryHandler(
            task_repo=bundle.pm.task_repo,
            assignment_repo=bundle.pm.assignment_repo,
            user_session=user_session,
        ),
        hierarchy_query_handler=TaskHierarchyQueryHandler(
            task_repo=bundle.pm.task_repo,
            work_calendar_engine=work_calendar_engine,
            user_session=user_session,
        ),
    )
    return TaskApprovalDeps(task_service=task_service)


__all__ = ["build_task_approval_deps"]
