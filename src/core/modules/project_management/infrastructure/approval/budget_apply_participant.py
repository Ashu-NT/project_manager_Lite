"""Session-parameterized approval transaction participant for
`budget.approve`/`reject`.

Constructs a fresh `BudgetService` bound to whichever Session
`build_budget_approval_deps(session, ...)` was called with (never the
shared startup instance), then calls its own
`_apply_approval_decision`/`_apply_rejection_decision` directly rather
than duplicating them.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.application.financials.budgets.budget_service import (
    BudgetService,
)
from src.core.modules.project_management.infrastructure.approval._financial_decision_actor import (
    require_financial_decision_actor,
)
from src.core.platform.contract.models.approval.contracts import ApprovalHandlerResult
from src.core.platform.domain.approval import ApprovalRequest


@dataclass(frozen=True)
class BudgetApprovalDeps:
    """`budget_service` is a fresh `BudgetService`, constructed with
    `approval_service=None` -- the apply path never calls back into
    `ApprovalService`."""

    budget_service: BudgetService


class BudgetApprovalParticipant:
    def apply(self, request: ApprovalRequest, deps: BudgetApprovalDeps) -> ApprovalHandlerResult:
        approved_by = require_financial_decision_actor(deps.budget_service._user_session)
        _budget, events = deps.budget_service._apply_approval_decision(
            budget_id=request.payload["budget_id"],
            approved_by=approved_by,
            expected_version=request.payload["expected_version"],
            notes=request.payload.get("notes", ""),
        )
        return ApprovalHandlerResult(domain_events=events)

    def reject(self, request: ApprovalRequest, deps: BudgetApprovalDeps) -> ApprovalHandlerResult:
        rejected_by = require_financial_decision_actor(deps.budget_service._user_session)
        _budget, event = deps.budget_service._apply_rejection_decision(
            budget_id=request.payload["budget_id"],
            rejected_by=rejected_by,
            expected_version=request.payload["expected_version"],
            notes=request.payload.get("notes", ""),
        )
        return ApprovalHandlerResult(domain_events=(event,))


__all__ = ["BudgetApprovalDeps", "BudgetApprovalParticipant"]
