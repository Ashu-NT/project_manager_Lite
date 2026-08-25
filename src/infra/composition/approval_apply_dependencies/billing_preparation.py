"""P4-PRE Step 1 (ADR-005 Section 24, Round 8): `dependencies_factory(session)` for
`project_billing_preparation.approve`.

Follows `budget.py`'s reference template. `ProjectBillingPreparationService` is the most
collaborator-heavy of the eight approval-backed families: besides its own repositories, its real
constructor (see `project_registry.py`'s `billing_preparation_service = ProjectBillingPreparationService(...)`
call site) takes two further collaborators that are themselves Session-bound and therefore cannot
be reused from the long-lived, startup-bound instances:

- `rate_resolver` (`RateCardResolver`) wraps a `SqlAlchemyRateResolutionReader(session=...)` --
  a fresh reader (and therefore a fresh resolver) is built here, bound to the supplied Session.
- `financial_period_service` (`FinancialPeriodService`) is itself constructed with
  `session=...`/`period_repo=...` in `platform_registry.py` -- a fresh instance is built here too,
  bound to the supplied Session and sharing the same fresh `EnterpriseAuditService` this factory
  builds for `ProjectBillingPreparationService` itself (both act within the same approval-apply
  transaction).

`_apply_approval_decision`/`_apply_rejection_decision` themselves never call `_rate_resolver`,
`_financial_period_service`, `_cost_entry_repo`, or `_labor_posting_repo` -- but the service's
constructor requires all of them regardless, so each is still built fresh and correctly
Session-bound for construction-correctness, even though only `_billing_repo` (and the audit path)
is actually exercised by the two governed-decision methods.
"""

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
    """Every transaction-sensitive collaborator (every repository, the rate resolver's reader,
    `FinancialPeriodService`, and `ProjectBillingPreparationService` itself) is constructed fresh,
    bound to `session` -- never the caller's own, possibly different, Session.
    `user_session`/`tenant_context_service`/`module_catalog_service` are ambient,
    stateless-with-respect-to-this-transaction collaborators, passed through as-is (ADR-005
    Section 24, Round 7's "ambient collaborators ... may be reused as-is" rule). `approval_service`
    is deliberately omitted -- see `billing_preparation_apply_participant.py`'s module docstring."""
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
