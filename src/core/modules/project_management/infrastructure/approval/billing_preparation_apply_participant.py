"""Session-parameterized approval transaction participant for
`project_billing_preparation.approve`/`reject`.

Constructs a fresh `ProjectBillingPreparationService` bound to whichever
Session `build_billing_preparation_approval_deps(session, ...)` was called
with (never the shared startup instance), then calls its
`_apply_approval_decision`/`_apply_rejection_decision` directly rather than
duplicating them.

Passes ``expected_version + 1``, not the raw submitted value: `+1`
accounts for the row-version bump `submit_preparation()` itself performed
when it moved the preparation to `submitted`.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.application.financials.invoicing.preparation_service import (
    ProjectBillingPreparationService,
)
from src.core.modules.project_management.infrastructure.approval._financial_decision_actor import (
    require_financial_decision_actor,
)
from src.core.platform.contract.models.approval.contracts import ApprovalHandlerResult
from src.core.platform.domain.approval import ApprovalRequest


@dataclass(frozen=True)
class BillingPreparationApprovalDeps:
    """`billing_preparation_service` is a fresh `ProjectBillingPreparationService`,
    constructed with `approval_service=None` -- the apply path never calls
    back into `ApprovalService`."""

    billing_preparation_service: ProjectBillingPreparationService


class BillingPreparationApprovalParticipant:
    def apply(
        self, request: ApprovalRequest, deps: BillingPreparationApprovalDeps
    ) -> ApprovalHandlerResult:
        approved_by = require_financial_decision_actor(
            deps.billing_preparation_service._user_session
        )
        _preparation, event = deps.billing_preparation_service._apply_approval_decision(
            request.payload["preparation_id"],
            approved_by=approved_by,
            expected_version=request.payload["expected_version"] + 1,
        )
        return ApprovalHandlerResult(domain_events=(event,))

    def reject(
        self, request: ApprovalRequest, deps: BillingPreparationApprovalDeps
    ) -> ApprovalHandlerResult:
        rejected_by = require_financial_decision_actor(
            deps.billing_preparation_service._user_session
        )
        _preparation, event = deps.billing_preparation_service._apply_rejection_decision(
            request.payload["preparation_id"],
            rejected_by=rejected_by,
            expected_version=request.payload["expected_version"] + 1,
            notes=request.decision_note or "",
        )
        return ApprovalHandlerResult(domain_events=(event,))


__all__ = ["BillingPreparationApprovalDeps", "BillingPreparationApprovalParticipant"]
