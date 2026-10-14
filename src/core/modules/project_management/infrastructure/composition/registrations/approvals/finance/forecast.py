from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.application.financials.forecasts.commands.approval import (
    ForecastApprovalCommands,
)
from src.core.modules.project_management.infrastructure.approval.forecast_apply_participant import (
    ForecastApprovalDeps,
)
from src.core.modules.project_management.infrastructure.composition.registrations.approvals._shared import (
    build_approval_repository_context,
    build_enterprise_audit_service,
    wire_tenant_context_service,
)


def build_forecast_approval_deps(
    session: Session,
    *,
    user_session,
    tenant_context_service,
    module_catalog_service=None,
) -> ForecastApprovalDeps:
    bundle = build_approval_repository_context(session, tenant_context_service)
    forecast_repo = wire_tenant_context_service(
        bundle.pm.project_forecast_repo, tenant_context_service
    )
    audit = build_enterprise_audit_service(
        session,
        bundle,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
    forecast_commands = ForecastApprovalCommands(
        session=session,
        forecast_repo=forecast_repo,
        clock=SystemClock(),
        user_session=user_session,
        enterprise_audit_service=audit,
        module_catalog_service=module_catalog_service,
        tenant_context_service=tenant_context_service,
        approval_commands=None,
    )
    return ForecastApprovalDeps(forecast_commands=forecast_commands)


__all__ = ["build_forecast_approval_deps"]
