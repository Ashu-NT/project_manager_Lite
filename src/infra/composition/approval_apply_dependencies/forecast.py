from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.application.financials.forecasts.version_service import (
    ForecastVersionService,
)
from src.core.modules.project_management.infrastructure.approval.forecast_apply_participant import (
    ForecastApprovalDeps,
)
from src.infra.composition.approval_apply_dependencies._shared import (
    build_enterprise_audit_service,
    wire_tenant_context_service,
)
from src.infra.composition.repositories import build_repository_bundle


def build_forecast_approval_deps(
    session: Session,
    *,
    user_session,
    tenant_context_service,
    module_catalog_service=None,
) -> ForecastApprovalDeps:
    bundle = build_repository_bundle(session)
    forecast_repo = wire_tenant_context_service(
        bundle.project_forecast_repo, tenant_context_service
    )
    audit = build_enterprise_audit_service(
        session,
        bundle,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
    service = ForecastVersionService(
        session=session,
        forecast_repo=forecast_repo,
        project_repo=bundle.project_repo,
        financial_profile_repo=bundle.project_financial_profile_repo,
        cost_code_repo=bundle.project_cost_code_repo,
        task_repo=bundle.task_repo,
        clock=SystemClock(),
        user_session=user_session,
        enterprise_audit_service=audit,
        module_catalog_service=module_catalog_service,
        tenant_context_service=tenant_context_service,
        approval_service=None,
    )
    return ForecastApprovalDeps(forecast_service=service)


__all__ = ["build_forecast_approval_deps"]
