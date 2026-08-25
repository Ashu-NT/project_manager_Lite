"""P4-PRE Step 1 (ADR-005 Section 24, Round 8): module-owned, session-parameterized approval
transaction participant for `baseline.create` (apply only -- there is no `baseline.create`
reject handler).

Design note (verified during Step 1 implementation, following the pattern already validated for
`budget.approve`): `BaselineService`'s own `create_baseline()` calls
`_apply_baseline_creation_decision` directly for the *non-governed, direct-apply* case (see
`baseline_service.py:138`) -- this method is not exclusively reachable from the approval-composed
path, so it cannot be deleted or duplicated (a real, non-approval consumer would break, and a
duplicate copy would drift from the original over time). Per the "if shared logic is reused,
extract a lower-level operation rather than duplicate it" rule, this participant instead reuses
the method verbatim, unmodified, by constructing a fresh `BaselineService` instance -- bound to
whichever Session `build_baseline_approval_deps(session, ...)` was called with, and deliberately
never given `approval_service=` -- rather than reaching for the long-lived, permanently
shared-Session instance `project_registry.py` builds at startup. This is what makes the
approval-facing call genuinely session-parameterizable: given Session A it acts against A; given
Session B, against B; it never touches the startup Session by construction.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.core.modules.project_management.application.scheduling.baselines.baseline_service import (
    BaselineService,
)
from src.core.platform.contract.models.approval.contracts import (
    ApprovalHandlerResult,
    ApprovalPostCommitEvent,
)
from src.core.platform.domain.approval import ApprovalRequest


@dataclass(frozen=True)
class BaselineApprovalDeps:
    """`baseline_service` is a fresh `BaselineService`, bound to the Session
    `build_baseline_approval_deps(session, ...)` was called with, constructed with
    `approval_service=None` -- the apply path never calls back into `ApprovalService` (it only
    ever needs to *apply* an already-decided request, never to *request* a new one)."""

    baseline_service: BaselineService


class BaselineApprovalParticipant:
    def apply(
        self, request: ApprovalRequest, deps: BaselineApprovalDeps
    ) -> ApprovalHandlerResult:
        project_id = request.payload["project_id"]
        deps.baseline_service._apply_baseline_creation_decision(
            project_id=project_id,
            name=request.payload.get("name") or "Baseline",
            rate_as_of=date.today(),
            commit=False,
        )
        return ApprovalHandlerResult(
            post_commit_events=(ApprovalPostCommitEvent("baseline_changed", project_id),)
        )


__all__ = ["BaselineApprovalDeps", "BaselineApprovalParticipant"]
