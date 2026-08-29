from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.application.financials.financial_changes.service import (
    FinancialChangeService,
)
from src.core.modules.project_management.application.financials.invalidation import (
    invalidation_scope,
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
        events = [
            ApprovalPostCommitEvent(
                "financial_changes_changed", invalidation_scope(change)
            )
        ]
        if change.applied_budget_id:
            events.append(ApprovalPostCommitEvent("budgets_changed", change.project_id))
        if change.applied_forecast_id:
            events.append(
                ApprovalPostCommitEvent(
                    "forecasts_changed", invalidation_scope(change)
                )
            )
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
                ApprovalPostCommitEvent(
                    "financial_changes_changed", invalidation_scope(change)
                ),
            )
        )


__all__ = ["FinancialChangeApprovalDeps", "FinancialChangeApprovalParticipant"]
