"""Session-parameterized approval transaction participant for
`budget.approve`/`reject`.

Constructs a fresh `BudgetApprovalCommands` bound to whichever Session
`build_budget_approval_deps(session, ...)` was called with (never the
shared startup instance), then calls its own
`_apply_approval_decision`/`_apply_rejection_decision` directly rather
than duplicating them.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.application.financials.budgets.commands.approval import (
    BudgetApprovalCommands,
)
from src.core.modules.project_management.infrastructure.approval._financial_decision_actor import (
    require_financial_decision_actor,
)
from src.core.platform.contract.models.approval.contracts import ApprovalHandlerResult
from src.core.platform.domain.approval import ApprovalRequest


@dataclass(frozen=True)
class BudgetApprovalDeps:
    """`budget_commands` is a fresh `BudgetApprovalCommands`, constructed with
    `approval_commands=None` -- the apply path never calls back into
    `ApprovalCommands`."""

    budget_commands: BudgetApprovalCommands


class BudgetApprovalParticipant:
    def apply(self, request: ApprovalRequest, deps: BudgetApprovalDeps) -> ApprovalHandlerResult:
        approved_by = require_financial_decision_actor(deps.budget_commands._user_session)
        _budget, events = deps.budget_commands._apply_approval_decision(
            budget_id=request.payload["budget_id"],
            approved_by=approved_by,
            expected_version=request.payload["expected_version"],
            notes=request.payload.get("notes", ""),
        )
        return ApprovalHandlerResult(domain_events=events)

    def reject(self, request: ApprovalRequest, deps: BudgetApprovalDeps) -> ApprovalHandlerResult:
        rejected_by = require_financial_decision_actor(deps.budget_commands._user_session)
        _budget, event = deps.budget_commands._apply_rejection_decision(
            budget_id=request.payload["budget_id"],
            rejected_by=rejected_by,
            expected_version=request.payload["expected_version"],
            notes=request.payload.get("notes", ""),
        )
        return ApprovalHandlerResult(domain_events=(event,))


__all__ = ["BudgetApprovalDeps", "BudgetApprovalParticipant"]
