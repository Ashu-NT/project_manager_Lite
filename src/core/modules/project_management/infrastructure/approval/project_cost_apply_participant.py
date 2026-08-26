

from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.application.financials.cost.entries.cost_entry_service import (
    ProjectCostEntryService,
)
from src.core.modules.project_management.infrastructure.approval._financial_decision_actor import (
    require_financial_decision_actor,
)
from src.core.platform.contract.models.approval.contracts import ApprovalHandlerResult
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
        deps.cost_entry_service._apply_approval_decision(
            entry_id=request.payload["entry_id"],
            expected_version=request.payload["expected_version"],
            actor_id=approved_by,
            commit=False,
        )
        return ApprovalHandlerResult()

    def reject(
        self, request: ApprovalRequest, deps: ProjectCostApprovalDeps
    ) -> ApprovalHandlerResult:
        rejected_by = require_financial_decision_actor(deps.cost_entry_service._user_session)
        deps.cost_entry_service._apply_rejection_decision(
            entry_id=request.payload["entry_id"],
            expected_version=request.payload["expected_version"],
            actor_id=rejected_by,
            notes=request.payload.get("notes", ""),
            commit=False,
        )
        return ApprovalHandlerResult()


__all__ = ["ProjectCostApprovalDeps", "ProjectCostApprovalParticipant"]
