"""P4-PRE Step 1 (ADR-005 Section 24, Round 8): module-owned, session-parameterized approval
transaction participant for `budget.approve`.

Design note (discovered during Step 1 implementation, not assumed up front): `BudgetService`'s
own `approve_budget()`/`reject_budget()` call `_apply_approval_decision`/`_apply_rejection_decision`
directly for the *non-governed, direct-apply* case -- these methods are not exclusively reachable
from the approval-composed path, so they cannot be deleted or duplicated (a real, non-approval
consumer would break, and a duplicate copy would drift from the original over time). Per the
"if shared logic is reused, extract a lower-level operation rather than duplicate it" rule, this
participant instead reuses the method verbatim, unmodified, by constructing a fresh
`BudgetService` instance -- bound to whichever Session `build_budget_approval_deps(session, ...)`
was called with, and deliberately never given `approval_service=` -- rather than reaching for the
long-lived, permanently shared-Session instance `project_registry.py` builds at startup. This is
what makes the approval-facing call genuinely session-parameterizable: given Session A it acts
against A; given Session B, against B; it never touches the startup Session by construction.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.application.financials.budgets.budget_service import (
    BudgetService,
)
from src.core.modules.project_management.infrastructure.approval._financial_decision_actor import (
    require_financial_decision_actor,
)
from src.core.platform.contract.models.approval.contracts import (
    ApprovalHandlerResult,
    ApprovalPostCommitEvent,
)
from src.core.platform.domain.approval import ApprovalRequest


@dataclass(frozen=True)
class BudgetApprovalDeps:
    """`budget_service` is a fresh `BudgetService`, bound to the Session
    `build_budget_approval_deps(session, ...)` was called with, constructed with
    `approval_service=None` -- the apply path never calls back into `ApprovalService` (confirmed
    by the P4A investigation: the circular reference on the long-lived instance exists only for
    its own, unrelated, outbound `request_change(...)` calls)."""

    budget_service: BudgetService


class BudgetApprovalParticipant:
    def apply(self, request: ApprovalRequest, deps: BudgetApprovalDeps) -> ApprovalHandlerResult:
        approved_by = require_financial_decision_actor(deps.budget_service._user_session)
        budget = deps.budget_service._apply_approval_decision(
            budget_id=request.payload["budget_id"],
            approved_by=approved_by,
            expected_version=request.payload["expected_version"],
            notes=request.payload.get("notes", ""),
        )
        return ApprovalHandlerResult(
            post_commit_events=(ApprovalPostCommitEvent("budgets_changed", budget.project_id),)
        )

    def reject(self, request: ApprovalRequest, deps: BudgetApprovalDeps) -> ApprovalHandlerResult:
        rejected_by = require_financial_decision_actor(deps.budget_service._user_session)
        budget = deps.budget_service._apply_rejection_decision(
            budget_id=request.payload["budget_id"],
            rejected_by=rejected_by,
            expected_version=request.payload["expected_version"],
            notes=request.payload.get("notes", ""),
        )
        return ApprovalHandlerResult(
            post_commit_events=(ApprovalPostCommitEvent("budgets_changed", budget.project_id),)
        )


__all__ = ["BudgetApprovalDeps", "BudgetApprovalParticipant"]
