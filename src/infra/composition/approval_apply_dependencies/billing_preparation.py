from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.application.financials.invoicing.preparation_service import (
    ProjectBillingPreparationService,
)
from src.core.modules.project_management.application.financials.rate_cards.rate_card_resolver import (
    RateCardResolver,
)
from src.core.modules.project_management.infrastructure.approval.billing_preparation_apply_participant import (
    BillingPreparationApprovalDeps,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.rate_cards.rate_resolution_reader import (
    SqlAlchemyRateResolutionReader,
)
from src.core.platform.application.finance.financial_period_service import FinancialPeriodService
from src.infra.composition.approval_apply_dependencies._shared import (
    build_enterprise_audit_service,
    wire_tenant_context_service,
)
from src.infra.composition.repositories import build_repository_bundle


def build_billing_preparation_approval_deps(
    session: Session,
    *,
    user_session,
    tenant_context_service,
    module_catalog_service=None,
) -> BillingPreparationApprovalDeps:

    bundle = build_repository_bundle(session)
    billing_repo = wire_tenant_context_service(bundle.project_billing_repo, tenant_context_service)
    financial_profile_repo = wire_tenant_context_service(
        bundle.project_financial_profile_repo, tenant_context_service
    )
    cost_entry_repo = wire_tenant_context_service(
        bundle.project_cost_entry_repo, tenant_context_service
    )
    labor_posting_repo = wire_tenant_context_service(
        bundle.approved_time_labor_posting_repo, tenant_context_service
    )
    financial_period_repo = wire_tenant_context_service(
        bundle.financial_period_repo, tenant_context_service
    )
    clock = SystemClock()
    enterprise_audit_service = build_enterprise_audit_service(
        session,
        bundle,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
    rate_resolver = RateCardResolver(
        reader=SqlAlchemyRateResolutionReader(session),
        tenant_context_service=tenant_context_service,
        clock=clock,
    )
    financial_period_service = FinancialPeriodService(
        session=session,
        period_repo=financial_period_repo,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
    )
    billing_preparation_service = ProjectBillingPreparationService(
        session=session,
        billing_repo=billing_repo,
        financial_profile_repo=financial_profile_repo,
        cost_entry_repo=cost_entry_repo,
        labor_posting_repo=labor_posting_repo,
        rate_resolver=rate_resolver,
        financial_period_service=financial_period_service,
        approval_service=None,
        tenant_context_service=tenant_context_service,
        clock=clock,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        module_catalog_service=module_catalog_service,
    )
    return BillingPreparationApprovalDeps(billing_preparation_service=billing_preparation_service)


__all__ = ["build_billing_preparation_approval_deps"]
