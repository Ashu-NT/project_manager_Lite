"""P4-PRE Step 1 (ADR-005 Section 24, Round 8): module-owned, session-parameterized approval
transaction participant for `project_cost.approve`.

Design note (confirmed by grep, not assumed up front): `ProjectCostEntryService`'s own
`approve()`/`reject()` call `_apply_approval_decision`/`_apply_rejection_decision` directly for
the *non-governed, direct-apply* case (`cost_entry_service.py:601` and `:624`) -- these methods
are not exclusively reachable from the approval-composed path, so they cannot be deleted or
duplicated (a real, non-approval consumer would break, and a duplicate copy would drift from the
original over time). Per the "if shared logic is reused, extract a lower-level operation rather
than duplicate it" rule, this participant instead reuses the method verbatim, unmodified, by
constructing a fresh `ProjectCostEntryService` instance -- bound to whichever Session
`build_project_cost_approval_deps(session, ...)` was called with, and deliberately never given
`approval_service=` -- rather than reaching for the long-lived, permanently shared-Session
instance `project_registry.py` builds at startup. This is what makes the approval-facing call
genuinely session-parameterizable: given Session A it acts against A; given Session B, against B;
it never touches the startup Session by construction.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.application.financials.cost.entries.cost_entry_service import (
    ProjectCostEntryService,
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
class ProjectCostApprovalDeps:
    """`cost_entry_service` is a fresh `ProjectCostEntryService`, bound to the Session
    `build_project_cost_approval_deps(session, ...)` was called with, constructed with
    `approval_service=None` -- the apply path never calls back into `ApprovalService` (same
    reasoning as `BudgetApprovalDeps`: the circular reference on the long-lived instance exists
    only for its own, unrelated, outbound `request_change(...)` calls)."""

    cost_entry_service: ProjectCostEntryService


class ProjectCostApprovalParticipant:
    def apply(
        self, request: ApprovalRequest, deps: ProjectCostApprovalDeps
    ) -> ApprovalHandlerResult:
        approved_by = require_financial_decision_actor(deps.cost_entry_service._user_session)
        entry = deps.cost_entry_service._apply_approval_decision(
            entry_id=request.payload["entry_id"],
            expected_version=request.payload["expected_version"],
            actor_id=approved_by,
            commit=False,
        )
        return ApprovalHandlerResult(
            post_commit_events=(ApprovalPostCommitEvent("cost_entries_changed", entry.project_id),)
        )

    def reject(
        self, request: ApprovalRequest, deps: ProjectCostApprovalDeps
    ) -> ApprovalHandlerResult:
        rejected_by = require_financial_decision_actor(deps.cost_entry_service._user_session)
        entry = deps.cost_entry_service._apply_rejection_decision(
            entry_id=request.payload["entry_id"],
            expected_version=request.payload["expected_version"],
            actor_id=rejected_by,
            notes=request.payload.get("notes", ""),
            commit=False,
        )
        return ApprovalHandlerResult(
            post_commit_events=(ApprovalPostCommitEvent("cost_entries_changed", entry.project_id),)
        )


__all__ = ["ProjectCostApprovalDeps", "ProjectCostApprovalParticipant"]
