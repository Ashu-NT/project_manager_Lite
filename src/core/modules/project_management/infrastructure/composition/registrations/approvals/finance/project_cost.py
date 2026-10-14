from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.application.financials.cost.entries.commands.review import (
    ProjectCostEntryReviewCommandHandler,
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
    financial_period_queries,
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
    cost_entry_commands = ProjectCostEntryReviewCommandHandler(
        session=session,
        entry_repo=entry_repo,
        clock=SystemClock(),
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        activity_service=None,
        module_catalog_service=module_catalog_service,
        approval_commands=None,
        record_event=None,
    )
    return ProjectCostApprovalDeps(cost_entry_commands=cost_entry_commands)


__all__ = ["build_project_cost_approval_deps"]
