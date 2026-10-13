from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.application.financials.cost.entries.cost_entry_service import (
    ProjectCostEntryService,
)
from src.core.modules.project_management.infrastructure.approval.project_cost_apply_participant import (
    ProjectCostApprovalDeps,
)
from src.core.modules.project_management.infrastructure.composition.registrations.approvals._shared import (
    build_approval_repository_context,
    build_enterprise_audit_service,
    wire_tenant_context_service,
)


def build_project_cost_approval_deps(
    session: Session,
    *,
    user_session,
    tenant_context_service,
    financial_period_service,
    module_catalog_service=None,
) -> ProjectCostApprovalDeps:

    bundle = build_approval_repository_context(session, tenant_context_service)
    entry_repo = wire_tenant_context_service(
        bundle.pm.project_cost_entry_repo, tenant_context_service
    )
    enterprise_audit_service = build_enterprise_audit_service(
        session,
        bundle,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
    cost_entry_service = ProjectCostEntryService(
        session=session,
        entry_repo=entry_repo,
        project_repo=bundle.pm.project_repo,
        financial_profile_repo=bundle.pm.project_financial_profile_repo,
        cost_code_repo=bundle.pm.project_cost_code_repo,
        task_repo=bundle.pm.task_repo,
        resource_repo=bundle.pm.resource_repo,
        financial_period_service=financial_period_service,
        clock=SystemClock(),
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        module_catalog_service=module_catalog_service,
        tenant_context_service=tenant_context_service,
        approval_service=None,
    )
    return ProjectCostApprovalDeps(cost_entry_service=cost_entry_service)


__all__ = ["build_project_cost_approval_deps"]
