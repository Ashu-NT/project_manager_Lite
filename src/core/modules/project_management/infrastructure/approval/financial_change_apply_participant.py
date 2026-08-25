"""P4-PRE Step 1 (ADR-005 Section 24, Round 8): module-owned, session-parameterized approval
transaction participant for `financial_change.apply`.

Design note (discovered during Step 1 implementation, not assumed up front): unlike Budget,
Task, Baseline, and ProjectCostEntry, `FinancialChangeService` has NO direct-apply
(non-governed) path -- `grep -rn "_apply_approval_decision\\|_apply_rejection_decision"` over
`financial_changes/` finds only the method definitions themselves, and the only *callers* are
the `financial_change.apply` approval-registration closures in `project_registry.py`. A financial
change can only ever be applied or rejected by going through `ApprovalService` (there is no
`approve_change()`/`reject_change()` sibling of `approve_budget()`/`reject_budget()`). Even so,
per the P4-PRE Step 1 convention shared by all 8 families being extracted in parallel, this
participant still reuses `_apply_approval_decision`/`_apply_rejection_decision` verbatim,
unmodified, by constructing a fresh `FinancialChangeService` instance -- bound to whichever
Session `build_financial_change_approval_deps(session, ...)` was called with -- rather than
duplicating their bodies or reaching for the long-lived, permanently shared-Session instance
`project_registry.py` builds at startup.

`financial_change.apply`'s apply path is the most complex of the financial-change families:
applying a change can cascade into a new budget successor, a new forecast successor, and/or
task schedule updates, so the number of post-commit events is variable. This mirrors the
`_apply_financial_change` closure's conditional event-building exactly:
`financial_changes_changed` always fires; `budgets_changed`, `forecasts_changed`, and
`tasks_changed` fire only when the applied change actually produced that kind of successor
(`change.applied_budget_id`/`applied_forecast_id`/`applied_schedule_count`, respectively). The
reject path only ever emits `financial_changes_changed`.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.application.financials.financial_changes.service import (
    FinancialChangeService,
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
class FinancialChangeApprovalDeps:
    """`financial_change_service` is a fresh `FinancialChangeService`, bound to the Session
    `build_financial_change_approval_deps(session, ...)` was called with, constructed with
    `approval_service=None` -- the apply path never calls back into `ApprovalService` (same
    P4A finding as the other three financial families: the circular reference on the long-lived
    instance exists only for its own, unrelated, outbound `request_change(...)` call from
    `submit_change()`, which this participant never invokes)."""

    financial_change_service: FinancialChangeService


class FinancialChangeApprovalParticipant:
    def apply(
        self, request: ApprovalRequest, deps: FinancialChangeApprovalDeps
    ) -> ApprovalHandlerResult:
        applied_by = require_financial_decision_actor(
            deps.financial_change_service._user_session
        )
        change = deps.financial_change_service._apply_approval_decision(
            change_id=request.payload["change_id"],
            approval_request_id=request.id,
            applied_by=applied_by,
            commit=False,
        )
        events = [ApprovalPostCommitEvent("financial_changes_changed", change.project_id)]
        if change.applied_budget_id:
            events.append(ApprovalPostCommitEvent("budgets_changed", change.project_id))
        if change.applied_forecast_id:
            events.append(ApprovalPostCommitEvent("forecasts_changed", change.project_id))
        if change.applied_schedule_count:
            events.append(ApprovalPostCommitEvent("tasks_changed", change.project_id))
        return ApprovalHandlerResult(post_commit_events=tuple(events))

    def reject(
        self, request: ApprovalRequest, deps: FinancialChangeApprovalDeps
    ) -> ApprovalHandlerResult:
        rejected_by = require_financial_decision_actor(
            deps.financial_change_service._user_session
        )
        change = deps.financial_change_service._apply_rejection_decision(
            change_id=request.payload["change_id"],
            approval_request_id=request.id,
            rejected_by=rejected_by,
            notes=request.decision_note or "",
            commit=False,
        )
        return ApprovalHandlerResult(
            post_commit_events=(
                ApprovalPostCommitEvent("financial_changes_changed", change.project_id),
            )
        )


__all__ = ["FinancialChangeApprovalDeps", "FinancialChangeApprovalParticipant"]
