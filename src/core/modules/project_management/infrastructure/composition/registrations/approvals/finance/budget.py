from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.application.financials.budgets.budget_service import (
    BudgetService,
)
from src.core.modules.project_management.infrastructure.approval.budget_apply_participant import (
    BudgetApprovalDeps,
)
from src.core.modules.project_management.infrastructure.composition.registrations.approvals._shared import (
    build_approval_repository_context,
    build_enterprise_audit_service,
    wire_tenant_context_service,
)


def build_budget_approval_deps(
    session: Session,
    *,
    user_session,
    tenant_context_service,
    module_catalog_service=None,
) -> BudgetApprovalDeps:
  
    bundle = build_approval_repository_context(session, tenant_context_service)
    budget_repo = wire_tenant_context_service(bundle.pm.project_budget_repo, tenant_context_service)
    enterprise_audit_service = build_enterprise_audit_service(
        session,
        bundle,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
    budget_service = BudgetService(
        session=session,
        budget_repo=budget_repo,
        project_repo=bundle.pm.project_repo,
        financial_profile_repo=bundle.pm.project_financial_profile_repo,
        cost_code_repo=bundle.pm.project_cost_code_repo,
        task_repo=bundle.pm.task_repo,
        clock=SystemClock(),
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        module_catalog_service=module_catalog_service,
        tenant_context_service=tenant_context_service,
        approval_service=None,
    )
    return BudgetApprovalDeps(budget_service=budget_service)


__all__ = ["build_budget_approval_deps"]
