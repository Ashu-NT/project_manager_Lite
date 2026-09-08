"""P4-PRE Step 1 (ADR-005 Section 24, Round 8): module-owned, session-parameterized approval
transaction participant for `project_billing_preparation.approve`.

Design note (confirmed by grep, not assumed up front): unlike Budget/Task/Baseline/
ProjectCostEntry, `ProjectBillingPreparationService`'s `_apply_approval_decision`/
`_apply_rejection_decision` have exactly one caller each in the whole codebase --
`project_registry.py`'s own `_approve_billing_preparation`/`_reject_billing_preparation`
closures. `ProjectBillingPreparationService` exposes no public, non-governed
`approve_preparation()`/`reject_preparation()` direct-apply method the way `BudgetService.
approve_budget()` does -- the only path onto a submitted preparation is the governed
`submit_preparation()` -> `ApprovalService.request_change(...)` -> apply/reject flow. Even so,
per the same "reuse rather than duplicate" rule (and for consistency with the other seven
families), this participant does not inline the method bodies: it constructs a fresh
`ProjectBillingPreparationService` instance -- bound to whichever Session
`build_billing_preparation_approval_deps(session, ...)` was called with, and deliberately never
given `approval_service=` -- rather than reaching for the long-lived, permanently shared-Session
instance `project_registry.py` builds at startup. This is what makes the approval-facing call
genuinely session-parameterizable: given Session A it acts against A; given Session B, against B;
it never touches the startup Session by construction.

The registry closures reproduced here pass ``req.payload["expected_version"] + 1`` (not the raw
submitted value) to both `_apply_approval_decision` and `_apply_rejection_decision` -- `+ 1`
accounts for the row-version bump `submit_preparation()` itself performed when it moved the
preparation from `draft`/`reserved` to `submitted`. This participant reproduces that `+ 1`
verbatim.

P39: `_apply_approval_decision`/`_apply_rejection_decision` no longer take a `commit` flag --
transaction ownership converged onto `FinanceGovernanceUnitOfWork` (the bespoke
`BillingPreparationSubmissionUnitOfWork` is retired entirely, no compatibility alias). Both
methods now unconditionally build their typed `BillingPreparationStatusChanged` fact and return
`(preparation, event)`, mirroring `ProjectCostEntryService`'s own dual-use shape: `record_event`
fires when wired (the governed direct path, unused here since these two methods are reachable
only from this participant), and the returned event is what this participant forwards via
`ApprovalHandlerResult(domain_events=(event,))` -- no more `ApprovalPostCommitEvent(
"billing_preparations_changed", ...)`.
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
    """`billing_preparation_service` is a fresh `ProjectBillingPreparationService`, bound to the
    Session `build_billing_preparation_approval_deps(session, ...)` was called with, constructed
    with `approval_service=None` -- the apply path never calls back into `ApprovalService` (same
    reasoning as `BudgetApprovalDeps`: the circular reference on the long-lived instance exists
    only for its own, unrelated, outbound `request_change(...)` call in `submit_preparation()`)."""

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
