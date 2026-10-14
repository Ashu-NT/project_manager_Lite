from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.application.financials.cost.entries.commands.review import (
    ProjectCostEntryReviewCommandHandler,
)
from src.core.modules.project_management.infrastructure.approval._financial_decision_actor import (
    require_financial_decision_actor,
)
from src.core.platform.contract.models.approval.contracts import ApprovalHandlerResult
from src.core.platform.domain.approval import ApprovalRequest


@dataclass(frozen=True)
class ProjectCostApprovalDeps:
    """Review commands share the deciding caller's session.

    Approval callbacks are disabled; this participant returns events and never commits.
    """

    cost_entry_commands: ProjectCostEntryReviewCommandHandler


class ProjectCostApprovalParticipant:
    def apply(
        self, request: ApprovalRequest, deps: ProjectCostApprovalDeps
    ) -> ApprovalHandlerResult:
        approved_by = require_financial_decision_actor(
            deps.cost_entry_commands._user_session
        )
        _entry, event = deps.cost_entry_commands._apply_approval_decision(
            entry_id=request.payload["entry_id"],
            expected_version=request.payload["expected_version"],
            actor_id=approved_by,
        )
        return ApprovalHandlerResult(domain_events=(event,))

    def reject(
        self, request: ApprovalRequest, deps: ProjectCostApprovalDeps
    ) -> ApprovalHandlerResult:
        rejected_by = require_financial_decision_actor(
            deps.cost_entry_commands._user_session
        )
        _entry, event = deps.cost_entry_commands._apply_rejection_decision(
            entry_id=request.payload["entry_id"],
            expected_version=request.payload["expected_version"],
            actor_id=rejected_by,
            notes=request.payload.get("notes", ""),
        )
        return ApprovalHandlerResult(domain_events=(event,))


__all__ = ["ProjectCostApprovalDeps", "ProjectCostApprovalParticipant"]
