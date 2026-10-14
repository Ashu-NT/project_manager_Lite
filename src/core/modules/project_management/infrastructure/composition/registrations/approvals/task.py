from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.scheduling import (
    ProjectCalendarAdapter,
    SchedulingEngine,
)
from src.core.modules.project_management.application.tasks.commands.dependency import (
    TaskDependencyCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.hierarchy_support import (
    TaskHierarchyPolicy,
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
from src.core.modules.project_management.application.tasks.queries.dependency_diagnostics import (
    TaskDependencyDiagnosticsQueryHandler,
)
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
    schedule_synchronizer = TaskScheduleSynchronizer(
        scheduling_engine=scheduling_engine,
        task_repo=bundle.pm.task_repo,
    )
    scheduling_constraint_handler = TaskSchedulingConstraintHandler(
        task_repo=bundle.pm.task_repo,
        user_session=user_session,
        approval_commands=None,
        tenant_context_service=tenant_context_service,
        scheduling_engine=scheduling_engine,
        work_calendar_engine=work_calendar_engine,
        schedule_synchronizer=schedule_synchronizer,
        uow_scope=task_uow_scope,
    )
    dependency_diagnostics_handler = TaskDependencyDiagnosticsQueryHandler(
        task_repo=bundle.pm.task_repo,
        dependency_repo=bundle.pm.dependency_repo,
        work_calendar_engine=work_calendar_engine,
        scheduling_engine=scheduling_engine,
        user_session=user_session,
    )
    dependencies = TaskDependencyCommandHandler(
            task_repo=bundle.pm.task_repo,
            dependency_repo=bundle.pm.dependency_repo,
            user_session=user_session,
            approval_commands=None,
            tenant_context_service=tenant_context_service,
            hierarchy_policy=hierarchy_policy,
            diagnostics_handler=dependency_diagnostics_handler,
            schedule_synchronizer=schedule_synchronizer,
            uow_scope=task_uow_scope,
        )
    leveling = ResourceLevelingCommandHandler(
            task_repo=bundle.pm.task_repo,
            assignment_repo=bundle.pm.assignment_repo,
            dependency_repo=bundle.pm.dependency_repo,
            resource_repo=bundle.pm.resource_repo,
            work_calendar_engine=work_calendar_engine,
            user_session=user_session,
            approval_commands=None,
            tenant_context_service=tenant_context_service,
            schedule_synchronizer=schedule_synchronizer,
            uow_scope=task_uow_scope,
        )
    return TaskApprovalDeps(dependencies=dependencies, constraints=scheduling_constraint_handler, leveling=leveling, uow_scope=task_uow_scope)


__all__ = ["build_task_approval_deps"]
