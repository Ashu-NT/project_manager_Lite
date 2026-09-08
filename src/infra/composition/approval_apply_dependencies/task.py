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
from src.core.platform.application.history.activity.activity_service import ActivityService
from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)
from src.infra.composition.approval_apply_dependencies._shared import wire_tenant_context_service
from src.infra.composition.repositories import build_repository_bundle


def build_task_approval_deps(
    session: Session,
    *,
    user_session,
    tenant_context_service,
    work_calendar_engine: CalendarProtocol,
    enterprise_calendar_resolver,
    calendar_assignment_service,
    module_catalog_service=None,
) -> TaskApprovalDeps:

    bundle = build_repository_bundle(session)

    for field_name in bundle.__dataclass_fields__:
        wire_tenant_context_service(getattr(bundle, field_name), tenant_context_service)

    activity_service = ActivityService(
        session=session,
        activity_repo=bundle.activity_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
    project_calendar_adapter = ProjectCalendarAdapter(
        resolver=enterprise_calendar_resolver,
        assignment_service=calendar_assignment_service,
    )
    scheduling_engine = SchedulingEngine(
        session,
        bundle.task_repo,
        bundle.dependency_repo,
        work_calendar_engine,
        assignment_repo=bundle.assignment_repo,
        resource_repo=bundle.resource_repo,
        project_calendar_adapter=project_calendar_adapter,
    )
    task_service = TaskService(
        session,
        bundle.task_repo,
        bundle.dependency_repo,
        bundle.assignment_repo,
        bundle.time_entry_repo,
        bundle.timesheet_period_repo,
        None,  # timesheet_service -- see module docstring
        bundle.resource_repo,
        work_calendar_engine,
        scheduling_engine,
        bundle.project_resource_repo,
        bundle.project_repo,
        user_session=user_session,
        activity_service=activity_service,
        approval_service=None,
        module_catalog_service=module_catalog_service,
        employee_repo=bundle.employee_repo,
        tenant_context_service=tenant_context_service,
    )
    return TaskApprovalDeps(task_service=task_service)


__all__ = ["build_task_approval_deps"]
