from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.scheduling.baselines.baseline_service import (
    BaselineService,
)
from src.core.modules.project_management.application.scheduling.services.scheduling_engine import (
    SchedulingEngine,
)
from src.core.modules.project_management.infrastructure.approval.baseline_apply_participant import (
    BaselineApprovalDeps,
)
from src.core.modules.project_management.infrastructure.composition.registrations.approvals._shared import (
    build_activity_service,
    build_approval_repository_context,
    wire_tenant_context_service,
)
from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)


def build_baseline_approval_deps(
    session: Session,
    *,
    user_session: Any,
    tenant_context_service: Any,
    calendar: CalendarProtocol,
    module_catalog_service: Any = None,
    calendar_resolver: Any = None,
    resource_calendar_map: dict[str, CalendarProtocol] | None = None,
    project_calendar_adapter: Any = None,
) -> BaselineApprovalDeps:

    bundle = build_approval_repository_context(session, tenant_context_service)
    project_repo = wire_tenant_context_service(bundle.pm.project_repo, tenant_context_service)
    task_repo = wire_tenant_context_service(bundle.pm.task_repo, tenant_context_service)
    dependency_repo = wire_tenant_context_service(bundle.pm.dependency_repo, tenant_context_service)
    assignment_repo = wire_tenant_context_service(bundle.pm.assignment_repo, tenant_context_service)
    resource_repo = wire_tenant_context_service(bundle.pm.resource_repo, tenant_context_service)
    planned_cost_repo = wire_tenant_context_service(
        bundle.pm.planned_cost_repo, tenant_context_service
    )
    baseline_repo = wire_tenant_context_service(bundle.pm.baseline_repo, tenant_context_service)

    scheduling_engine = SchedulingEngine(
        session,
        task_repo,
        dependency_repo,
        calendar,
        assignment_repo=assignment_repo,
        resource_repo=resource_repo,
        calendar_resolver=calendar_resolver,
        resource_calendar_map=resource_calendar_map,
        project_calendar_adapter=project_calendar_adapter,
    )
    activity_service = build_activity_service(
        session,
        bundle,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
    baseline_service = BaselineService(
        session=session,
        project_repo=project_repo,
        task_repo=task_repo,
        planned_cost_repo=planned_cost_repo,
        baseline_repo=baseline_repo,
        scheduling=scheduling_engine,
        calendar=calendar,
        user_session=user_session,
        activity_service=activity_service,
        approval_service=None,
        module_catalog_service=module_catalog_service,
        tenant_context_service=tenant_context_service,
    )
    return BaselineApprovalDeps(baseline_service=baseline_service)


__all__ = ["build_baseline_approval_deps"]
