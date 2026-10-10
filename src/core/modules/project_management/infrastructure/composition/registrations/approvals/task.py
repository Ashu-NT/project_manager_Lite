from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.scheduling import (
    ProjectCalendarAdapter,
    SchedulingEngine,
)
from src.core.modules.project_management.application.tasks.service import TaskService
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
    task_service = TaskService(
        session,
        bundle.pm.task_repo,
        bundle.pm.dependency_repo,
        bundle.pm.assignment_repo,
        bundle.platform.time_entry_repo,
        bundle.platform.timesheet_period_repo,
        None,  # timesheet_service -- see module docstring
        bundle.pm.resource_repo,
        work_calendar_engine,
        scheduling_engine,
        bundle.pm.project_resource_repo,
        bundle.pm.project_repo,
        user_session=user_session,
        activity_service=activity_service,
        approval_service=None,
        module_catalog_service=module_catalog_service,
        employee_repo=bundle.platform.employee_repo,
        tenant_context_service=tenant_context_service,
        enterprise_audit_service=enterprise_audit_service,
    )
    return TaskApprovalDeps(task_service=task_service)


__all__ = ["build_task_approval_deps"]
