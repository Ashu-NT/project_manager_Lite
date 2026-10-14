from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.application.financials.budgets.commands import (
    BudgetApprovalCommands,
)
from src.core.modules.project_management.application.financials.financial_changes.commands.approval import (
    FinancialChangeApprovalCommandHandler,
)
from src.core.modules.project_management.application.financials.forecasts.commands import (
    ForecastApprovalCommands,
)
from src.core.modules.project_management.infrastructure.approval.financial_change_apply_participant import (
    FinancialChangeApprovalDeps,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.finance.changes import (
    build_financial_change_schedule_port,
)
from src.core.modules.project_management.infrastructure.composition.registrations.approvals._shared import (
    build_approval_repository_context,
    build_enterprise_audit_service,
    wire_tenant_context_service,
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
    change_repo = wire_tenant_context_service(
        bundle.pm.financial_change_repo, tenant_context_service
    )
    budget_repo = wire_tenant_context_service(
        bundle.pm.project_budget_repo, tenant_context_service
    )
    forecast_repo = wire_tenant_context_service(
        bundle.pm.project_forecast_repo, tenant_context_service
    )

    enterprise_audit_service = build_enterprise_audit_service(
        session,
        bundle,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
    task_service = build_financial_change_schedule_port(
        session=session,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        work_calendar_engine=work_calendar_engine,
    )
    clock = SystemClock()
    budget_authority = BudgetApprovalCommands(
        session=session,
        budget_repo=budget_repo,
        clock=clock,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        module_catalog_service=module_catalog_service,
        tenant_context_service=tenant_context_service,
        approval_commands=None,
    )
    forecast_authority = ForecastApprovalCommands(
        session=session,
        forecast_repo=forecast_repo,
        clock=clock,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        module_catalog_service=module_catalog_service,
        tenant_context_service=tenant_context_service,
        record_event=record_event,
        approval_commands=None,
    )
    financial_change_commands = FinancialChangeApprovalCommandHandler(
        session=session,
        change_repo=change_repo,
        budget_repo=budget_repo,
        forecast_repo=forecast_repo,
        task_service=task_service,
        budget_authority=budget_authority,
        forecast_authority=forecast_authority,
        clock=clock,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        module_catalog_service=module_catalog_service,
    )
    return FinancialChangeApprovalDeps(
        financial_change_commands=financial_change_commands
    )


__all__ = ["build_financial_change_approval_deps"]
