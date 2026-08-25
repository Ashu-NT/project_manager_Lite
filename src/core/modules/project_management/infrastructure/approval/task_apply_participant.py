"""P4-PRE Step 1 (ADR-005 Section 24, Round 8): module-owned, session-parameterized approval
transaction participant for the Task family -- `dependency.add`, `dependency.remove`,
`dependency.update`, `task.constraint.update`, `scheduling.leveling.apply`.

Design note (mirrors the finding already documented for `budget.approve`, and confirmed here by
grep for ALL FIVE request types): none of `TaskDependencyMixin._apply_dependency_add_decision`
/`_apply_dependency_remove_decision`/`_apply_dependency_update_decision`,
`TaskSchedulingConstraintMixin._apply_task_scheduling_constraint_decision`, or
`ResourceLevelingApplyMixin._apply_resource_leveling_plan_decision` are exclusively reachable
from the approval-composed path -- each one is also called directly by `TaskService`'s own
public `add_dependency`/`remove_dependency`/`update_dependency`/
`update_task_scheduling_constraint`/`apply_resource_leveling_plan` for the *non-governed,
direct-apply* case. They cannot be deleted or duplicated (a real, non-approval consumer would
break, and a duplicate copy would drift from the original over time). Per the "if shared logic
is reused, extract a lower-level operation rather than duplicate it" rule, this participant
instead reuses each method verbatim, unmodified, by constructing a fresh `TaskService` instance
-- bound to whichever Session `build_task_approval_deps(session, ...)` was called with, and
deliberately never given `approval_service=` -- rather than reaching for the long-lived,
permanently shared-Session instance `project_registry.py` builds at startup. This is what makes
the approval-facing call genuinely session-parameterizable: given Session A it acts against A;
given Session B, against B; it never touches the startup Session by construction.

`_as_dependency_type`/`_as_optional_date` are moved here verbatim from `project_registry.py`
(confirmed via a grep for both names across ``src/`` to have no callers outside that file's own
Task approval-registration closures) since they exist solely to decode these five request types'
JSON payloads. `coerce_constraint_type` is NOT moved -- it is imported from its existing home,
`constraint_presentation.py`, which also backs the non-approval desktop API surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from src.core.modules.project_management.api.desktop.common.constraint_presentation import (
    coerce_constraint_type,
)
from src.core.modules.project_management.application.tasks.service import TaskService
from src.core.modules.project_management.domain.enums import DependencyType
from src.core.platform.contract.models.approval.contracts import (
    ApprovalHandlerResult,
    ApprovalPostCommitEvent,
)
from src.core.platform.domain.approval import ApprovalRequest


def _as_dependency_type(value: Any) -> DependencyType:
    if isinstance(value, DependencyType):
        return value
    return DependencyType((value or DependencyType.FINISH_TO_START.value))


def _as_optional_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


@dataclass(frozen=True)
class TaskApprovalDeps:
    """`task_service` is a fresh `TaskService`, bound to the Session
    `build_task_approval_deps(session, ...)` was called with, constructed with
    `approval_service=None` -- the apply path never calls back into `ApprovalService` (each of
    the five ``_apply_*_decision`` methods below is a pure re-fetch/re-validate/mutate operation;
    none of them raise `APPROVAL_REQUIRED` or otherwise reach for `self._approval_service`, that
    branching lives only in the public, non-underscore request-time methods this participant
    never calls)."""

    task_service: TaskService


class TaskApprovalParticipant:
    def apply_dependency_add(
        self, request: ApprovalRequest, deps: TaskApprovalDeps
    ) -> ApprovalHandlerResult:
        deps.task_service._apply_dependency_add_decision(
            predecessor_id=request.payload["predecessor_id"],
            successor_id=request.payload["successor_id"],
            dependency_type=_as_dependency_type(request.payload.get("dependency_type", "FS")),
            lag_days=int(request.payload.get("lag_days", 0) or 0),
            commit=False,
        )
        return ApprovalHandlerResult(
            post_commit_events=(ApprovalPostCommitEvent("tasks_changed", request.project_id or ""),)
        )

    def apply_dependency_remove(
        self, request: ApprovalRequest, deps: TaskApprovalDeps
    ) -> ApprovalHandlerResult:
        deps.task_service._apply_dependency_remove_decision(
            dependency_id=request.payload["dependency_id"],
            commit=False,
        )
        return ApprovalHandlerResult(
            post_commit_events=(ApprovalPostCommitEvent("tasks_changed", request.project_id or ""),)
        )

    def apply_dependency_update(
        self, request: ApprovalRequest, deps: TaskApprovalDeps
    ) -> ApprovalHandlerResult:
        deps.task_service._apply_dependency_update_decision(
            dependency_id=request.payload["dependency_id"],
            dependency_type=_as_dependency_type(request.payload.get("dependency_type", "FS")),
            lag_days=int(request.payload.get("lag_days", 0) or 0),
            expected_version=request.payload.get("expected_version"),
            commit=False,
        )
        return ApprovalHandlerResult(
            post_commit_events=(ApprovalPostCommitEvent("tasks_changed", request.project_id or ""),)
        )

    def apply_task_constraint_update(
        self, request: ApprovalRequest, deps: TaskApprovalDeps
    ) -> ApprovalHandlerResult:
        deps.task_service._apply_task_scheduling_constraint_decision(
            task_id=request.payload["task_id"],
            constraint_type=coerce_constraint_type(request.payload.get("constraint_type")),
            constraint_date=_as_optional_date(request.payload.get("constraint_date")),
            expected_version=request.payload.get("expected_version"),
            commit=False,
        )
        return ApprovalHandlerResult(
            post_commit_events=(ApprovalPostCommitEvent("tasks_changed", request.project_id or ""),)
        )

    def apply_resource_leveling_plan(
        self, request: ApprovalRequest, deps: TaskApprovalDeps
    ) -> ApprovalHandlerResult:
        deps.task_service._apply_resource_leveling_plan_decision(
            project_id=request.project_id,
            moves=request.payload["moves"],
            schedule_fingerprint=request.payload["schedule_fingerprint"],
            commit=False,
        )
        return ApprovalHandlerResult(
            post_commit_events=(ApprovalPostCommitEvent("tasks_changed", request.project_id or ""),)
        )


__all__ = ["TaskApprovalDeps", "TaskApprovalParticipant"]
