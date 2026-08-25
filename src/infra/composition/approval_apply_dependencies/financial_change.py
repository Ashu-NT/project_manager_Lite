"""P4-PRE Step 1 (ADR-005 Section 24, Round 8): `dependencies_factory(session)` for
`financial_change.apply`.

Follows the `budget.py` reference template. `FinancialChangeService` itself needs only fresh,
session-bound repositories (as Budget does), but its apply path can cascade into a task schedule
change (`FinancialChangeImpactType.SCHEDULE` impacts, applied via
`self._task_service._apply_approved_schedule_changes(...)`), so it also depends on a real
`ApprovedScheduleChangePort` implementation -- in production, `TaskService`. That, in turn, needs
its own fresh, session-bound collaborators (task/dependency/assignment/resource/project repos,
plus a fresh `SchedulingEngine` so `_sync_project_schedule` recalculates against *this* Session,
not the long-lived one) and a fresh `ActivityService` (so the schedule-change audit trail
`record_activity(..., commit=False)` writes land in the same transaction). `work_calendar_engine`
is accepted as a parameter (mirroring `platform_services.global_calendar_shim` at the
`project_registry.py` call site) because -- like `SystemClock` -- it holds no Session and is
genuinely ambient; it is the one dependency `FinancialChangeService`'s own family (Budget) never
needed to plumb through.

Deliberately left `None` on the fresh `TaskService`, because the schedule-change command mixin
(`ApprovedScheduleChangeMixin`) never touches them: `timesheet_service`, `notification_service`,
`employee_repo`, `assignment_skill_validator`, `enterprise_resource_availability_service`, and
`approval_service` (same never-reach-back-into-ApprovalService rule as every other financial
family). `TaskService`'s own docstring already treats this as a supported "lightweight
construction" -- e.g. the capacity check is skipped outright when
`enterprise_resource_availability_service` isn't configured -- rather than a hack unique to this
factory. The fresh `SchedulingEngine` is built without a `project_calendar_adapter`, so
`calendar_for_project` falls back to the plain `work_calendar_engine` instead of resolving a
project-specific enterprise calendar; this only affects which calendar governs working-day
validation for a schedule impact, not correctness of application.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.application.financials.financial_changes.service import (
    FinancialChangeService,
)
from src.core.modules.project_management.application.scheduling import SchedulingEngine
from src.core.modules.project_management.application.tasks import TaskService
from src.core.modules.project_management.infrastructure.approval.financial_change_apply_participant import (
    FinancialChangeApprovalDeps,
)
from src.core.platform.application.history.activity.activity_service import ActivityService
from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)
from src.infra.composition.approval_apply_dependencies._shared import (
    build_enterprise_audit_service,
    wire_tenant_context_service,
)
from src.infra.composition.repositories import build_repository_bundle


def build_financial_change_approval_deps(
    session: Session,
    *,
    user_session,
    tenant_context_service,
    work_calendar_engine: CalendarProtocol,
    module_catalog_service=None,
) -> FinancialChangeApprovalDeps:
    """Every transaction-sensitive collaborator -- every repository, the fresh
    `ActivityService`, the fresh `SchedulingEngine`, the fresh `TaskService`, and
    `FinancialChangeService` itself -- is constructed fresh, bound to `session`, never the
    caller's own, possibly different, Session. `user_session`/`tenant_context_service`/
    `module_catalog_service`/`work_calendar_engine` are ambient, stateless-with-respect-to-this-
    transaction collaborators, passed through as-is (ADR-005 Section 24, Round 7's "ambient
    collaborators ... may be reused as-is" rule). `approval_service` is deliberately omitted from
    both `TaskService` and `FinancialChangeService` -- see
    `financial_change_apply_participant.py`'s module docstring.
    """
    bundle = build_repository_bundle(session)
    change_repo = wire_tenant_context_service(bundle.financial_change_repo, tenant_context_service)
    budget_repo = wire_tenant_context_service(bundle.project_budget_repo, tenant_context_service)
    forecast_repo = wire_tenant_context_service(bundle.project_forecast_repo, tenant_context_service)
    project_repo = wire_tenant_context_service(bundle.project_repo, tenant_context_service)
    financial_profile_repo = wire_tenant_context_service(
        bundle.project_financial_profile_repo, tenant_context_service
    )
    cost_code_repo = wire_tenant_context_service(bundle.project_cost_code_repo, tenant_context_service)
    task_repo = wire_tenant_context_service(bundle.task_repo, tenant_context_service)
    dependency_repo = wire_tenant_context_service(bundle.dependency_repo, tenant_context_service)
    assignment_repo = wire_tenant_context_service(bundle.assignment_repo, tenant_context_service)
    resource_repo = wire_tenant_context_service(bundle.resource_repo, tenant_context_service)
    project_resource_repo = wire_tenant_context_service(
        bundle.project_resource_repo, tenant_context_service
    )
    activity_repo = wire_tenant_context_service(bundle.activity_repo, tenant_context_service)

    enterprise_audit_service = build_enterprise_audit_service(
        session,
        bundle,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
    activity_service = ActivityService(
        session=session,
        activity_repo=activity_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
    scheduling_engine = SchedulingEngine(
        session,
        task_repo,
        dependency_repo,
        work_calendar_engine,
        assignment_repo=assignment_repo,
        resource_repo=resource_repo,
    )
    task_service = TaskService(
        session,
        task_repo,
        dependency_repo,
        assignment_repo,
        None,
        None,
        None,
        resource_repo,
        work_calendar_engine,
        scheduling_engine=scheduling_engine,
        project_resource_repo=project_resource_repo,
        project_repo=project_repo,
        user_session=user_session,
        activity_service=activity_service,
        approval_service=None,
        module_catalog_service=module_catalog_service,
        tenant_context_service=tenant_context_service,
    )
    financial_change_service = FinancialChangeService(
        session=session,
        change_repo=change_repo,
        budget_repo=budget_repo,
        forecast_repo=forecast_repo,
        project_repo=project_repo,
        financial_profile_repo=financial_profile_repo,
        cost_code_repo=cost_code_repo,
        task_repo=task_repo,
        task_service=task_service,
        approval_service=None,
        clock=SystemClock(),
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        module_catalog_service=module_catalog_service,
        tenant_context_service=tenant_context_service,
    )
    return FinancialChangeApprovalDeps(financial_change_service=financial_change_service)


__all__ = ["build_financial_change_approval_deps"]
