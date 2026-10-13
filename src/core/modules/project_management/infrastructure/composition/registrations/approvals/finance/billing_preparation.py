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
from src.core.modules.project_management.infrastructure.composition.registrations.approvals._shared import (
    build_approval_repository_context,
    build_enterprise_audit_service,
    wire_tenant_context_service,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.rate_cards.rate_resolution_reader import (
    SqlAlchemyRateResolutionReader,
)
from src.core.platform.application.finance.financial_period_service import (
    FinancialPeriodService,
)


def build_billing_preparation_approval_deps(
    session: Session,
    *,
    user_session,
    tenant_context_service,
    module_catalog_service=None,
) -> BillingPreparationApprovalDeps:

    bundle = build_approval_repository_context(session, tenant_context_service)
    billing_repo = wire_tenant_context_service(bundle.pm.project_billing_repo, tenant_context_service)
    financial_profile_repo = wire_tenant_context_service(
        bundle.pm.project_financial_profile_repo, tenant_context_service
    )
    cost_entry_repo = wire_tenant_context_service(
        bundle.pm.project_cost_entry_repo, tenant_context_service
    )
    labor_posting_repo = wire_tenant_context_service(
        bundle.pm.approved_time_labor_posting_repo, tenant_context_service
    )
    financial_period_repo = wire_tenant_context_service(
        bundle.platform.financial_period_repo, tenant_context_service
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
        tenant_context_service=tenant_context_service,
        clock=clock,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        module_catalog_service=module_catalog_service,
    )
    return BillingPreparationApprovalDeps(billing_preparation_service=billing_preparation_service)


__all__ = ["build_billing_preparation_approval_deps"]
