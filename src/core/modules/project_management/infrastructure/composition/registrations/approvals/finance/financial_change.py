from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.application.financials.budgets.budget_service import (
    BudgetService,
)
from src.core.modules.project_management.application.financials.financial_changes.service import (
    FinancialChangeService,
)
from src.core.modules.project_management.application.financials.forecasts.version_service import (
    ForecastVersionService,
)
from src.core.modules.project_management.application.scheduling import SchedulingEngine
from src.core.modules.project_management.application.tasks import TaskService
from src.core.modules.project_management.infrastructure.approval.financial_change_apply_participant import (
    FinancialChangeApprovalDeps,
)
from src.core.modules.project_management.infrastructure.composition.registrations.approvals._shared import (
    build_approval_repository_context,
    build_enterprise_audit_service,
    wire_tenant_context_service,
)
from src.core.platform.application.history.activity.activity_service import (
    ActivityService,
)
from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)


def build_financial_change_approval_deps(
    session: Session,
    *,
    user_session,
    tenant_context_service,
    work_calendar_engine: CalendarProtocol,
    module_catalog_service=None,
    record_event=None,
) -> FinancialChangeApprovalDeps:
    bundle = build_approval_repository_context(session, tenant_context_service)
    change_repo = wire_tenant_context_service(bundle.pm.financial_change_repo, tenant_context_service)
    budget_repo = wire_tenant_context_service(bundle.pm.project_budget_repo, tenant_context_service)
    forecast_repo = wire_tenant_context_service(bundle.pm.project_forecast_repo, tenant_context_service)
    project_repo = wire_tenant_context_service(bundle.pm.project_repo, tenant_context_service)
    financial_profile_repo = wire_tenant_context_service(
        bundle.pm.project_financial_profile_repo, tenant_context_service
    )
    cost_code_repo = wire_tenant_context_service(bundle.pm.project_cost_code_repo, tenant_context_service)
    task_repo = wire_tenant_context_service(bundle.pm.task_repo, tenant_context_service)
    dependency_repo = wire_tenant_context_service(bundle.pm.dependency_repo, tenant_context_service)
    assignment_repo = wire_tenant_context_service(bundle.pm.assignment_repo, tenant_context_service)
    resource_repo = wire_tenant_context_service(bundle.pm.resource_repo, tenant_context_service)
    project_resource_repo = wire_tenant_context_service(
        bundle.pm.project_resource_repo, tenant_context_service
    )
    activity_repo = wire_tenant_context_service(bundle.platform.activity_repo, tenant_context_service)

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
        enterprise_audit_service=enterprise_audit_service,
    )
    clock = SystemClock()
    budget_authority = BudgetService(
        session=session,
        budget_repo=budget_repo,
        project_repo=project_repo,
        financial_profile_repo=financial_profile_repo,
        cost_code_repo=cost_code_repo,
        task_repo=task_repo,
        clock=clock,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        module_catalog_service=module_catalog_service,
        tenant_context_service=tenant_context_service,
        approval_service=None,
    )
    forecast_authority = ForecastVersionService(
        session=session,
        forecast_repo=forecast_repo,
        project_repo=project_repo,
        financial_profile_repo=financial_profile_repo,
        cost_code_repo=cost_code_repo,
        task_repo=task_repo,
        clock=clock,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        module_catalog_service=module_catalog_service,
        tenant_context_service=tenant_context_service,
        record_event=record_event,
        approval_service=None,
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
        budget_authority=budget_authority,
        forecast_authority=forecast_authority,
        approval_service=None,
        clock=clock,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        module_catalog_service=module_catalog_service,
        tenant_context_service=tenant_context_service,
    )
    return FinancialChangeApprovalDeps(financial_change_service=financial_change_service)


__all__ = ["build_financial_change_approval_deps"]
