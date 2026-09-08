"""Session-parameterized approval transaction participant for
`baseline.create` (apply only -- there is no `baseline.create` reject
handler).

Reuses `BaselineService._apply_baseline_creation_decision` verbatim rather
than duplicating it, by constructing a fresh `BaselineService` bound to
whichever Session `build_baseline_approval_deps(session, ...)` was called
with (never the shared startup instance) -- this is what makes the
approval-facing call session-parameterizable. `apply()` only flushes, never
commits; the caller owns the commit. Returns the typed
`ProjectBaselineCreated` fact via `ApprovalHandlerResult.domain_events`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

from src.core.modules.project_management.application.scheduling.baselines.baseline_events import (
    ProjectBaselineCreated,
)
from src.core.modules.project_management.application.scheduling.baselines.baseline_service import (
    BaselineService,
)
from src.core.platform.contract.models.approval.contracts import ApprovalHandlerResult
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
        baseline = deps.baseline_service._apply_baseline_creation_decision(
            project_id=project_id,
            name=request.payload.get("name") or "Baseline",
            rate_as_of=date.today(),
        )
        context = deps.baseline_service._require_context("create baseline")
        return ApprovalHandlerResult(
            domain_events=(
                ProjectBaselineCreated(
                    tenant_id=context.tenant_id,
                    organization_id=context.organization_id,
                    project_id=project_id,
                    baseline_id=baseline.id,
                    occurred_at=datetime.now(timezone.utc),
                ),
            )
        )


__all__ = ["BaselineApprovalDeps", "BaselineApprovalParticipant"]
