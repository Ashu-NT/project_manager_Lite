"""P4-PRE Step 1 (ADR-005 Section 24, Round 8): `dependencies_factory(session)` for
`project_cost.approve`.

Follows `budget.py` (the reference template for this package) exactly.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.application.financials.cost.entries.cost_entry_service import (
    ProjectCostEntryService,
)
from src.core.modules.project_management.infrastructure.approval.project_cost_apply_participant import (
    ProjectCostApprovalDeps,
)
from src.infra.composition.approval_apply_dependencies._shared import (
    build_enterprise_audit_service,
    wire_tenant_context_service,
)
from src.infra.composition.repositories import build_repository_bundle


def build_project_cost_approval_deps(
    session: Session,
    *,
    user_session,
    tenant_context_service,
    financial_period_service,
    module_catalog_service=None,
) -> ProjectCostApprovalDeps:
    """Every transaction-sensitive collaborator (every repository, and `ProjectCostEntryService`
    itself) is constructed fresh, bound to `session` -- never the caller's own, possibly
    different, Session. `user_session`/`tenant_context_service`/`module_catalog_service`/
    `financial_period_service` are ambient, stateless-with-respect-to-this-transaction
    collaborators, passed through as-is (ADR-005 Section 24, Round 7's "ambient collaborators
    ... may be reused as-is" rule). `approval_service` is deliberately omitted -- see
    `project_cost_apply_participant.py`'s module docstring. `rate_resolver`/`labor_posting_repo`
    are left unset -- they are only used by the trusted-inbox `apply_approved_time_source` path,
    never by `_apply_approval_decision`/`_apply_rejection_decision`."""
    bundle = build_repository_bundle(session)
    entry_repo = wire_tenant_context_service(
        bundle.project_cost_entry_repo, tenant_context_service
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
        project_repo=bundle.project_repo,
        financial_profile_repo=bundle.project_financial_profile_repo,
        cost_code_repo=bundle.project_cost_code_repo,
        task_repo=bundle.task_repo,
        resource_repo=bundle.resource_repo,
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
