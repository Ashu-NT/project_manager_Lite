"""Session-parameterized approval transaction participant for the Task
family -- `dependency.add`, `dependency.remove`, `dependency.update`,
`task.constraint.update`, `scheduling.leveling.apply`.

Constructs fresh command handlers bound to whichever Session
`build_task_approval_deps(session, ...)` was called with (never the
shared startup instance), then calls each request type's own
`_apply_*_decision` method directly rather than duplicating it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from src.core.modules.project_management.api.desktop.common.constraint_presentation import (
    coerce_constraint_type,
)
from src.core.modules.project_management.application.tasks.commands.dependency import (
    TaskDependencyCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.resource_leveling_apply import (
    ResourceLevelingCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.scheduling_constraint import (
    TaskSchedulingConstraintHandler,
)
from src.core.modules.project_management.application.tasks.task_unit_of_work_scope import (
    TaskUowScope,
)
from src.core.modules.project_management.domain.enums import DependencyType
from src.core.platform.contract.models.approval.contracts import ApprovalHandlerResult
from src.core.platform.domain.approval import ApprovalRequest


def _as_dependency_type(value: Any) -> DependencyType:
    if isinstance(value, DependencyType):
        return value
    return DependencyType(value or DependencyType.FINISH_TO_START.value)


def _as_optional_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


@dataclass(frozen=True)
class TaskApprovalDeps:
    """Fresh transaction-participant capabilities, constructed with
    `approval_commands=None` -- the apply path never calls back into
    `ApprovalCommands`."""

    dependencies: TaskDependencyCommandHandler
    constraints: TaskSchedulingConstraintHandler
    leveling: ResourceLevelingCommandHandler
    uow_scope: TaskUowScope


class TaskApprovalParticipant:
    def apply_dependency_add(
        self, request: ApprovalRequest, deps: TaskApprovalDeps
    ) -> ApprovalHandlerResult:
        deps.dependencies._apply_dependency_add_decision(
            predecessor_id=request.payload["predecessor_id"],
            successor_id=request.payload["successor_id"],
            dependency_type=_as_dependency_type(request.payload.get("dependency_type", "FS")),
            lag_days=int(request.payload.get("lag_days", 0) or 0),
        )
        return ApprovalHandlerResult(
            domain_events=deps.uow_scope.take_pending_events()
        )

    def apply_dependency_remove(
        self, request: ApprovalRequest, deps: TaskApprovalDeps
    ) -> ApprovalHandlerResult:
        deps.dependencies._apply_dependency_remove_decision(
            dependency_id=request.payload["dependency_id"],
        )
        return ApprovalHandlerResult(
            domain_events=deps.uow_scope.take_pending_events()
        )

    def apply_dependency_update(
        self, request: ApprovalRequest, deps: TaskApprovalDeps
    ) -> ApprovalHandlerResult:
        deps.dependencies._apply_dependency_update_decision(
            dependency_id=request.payload["dependency_id"],
            dependency_type=_as_dependency_type(request.payload.get("dependency_type", "FS")),
            lag_days=int(request.payload.get("lag_days", 0) or 0),
            expected_version=request.payload.get("expected_version"),
        )
        return ApprovalHandlerResult(
            domain_events=deps.uow_scope.take_pending_events()
        )

    def apply_task_constraint_update(
        self, request: ApprovalRequest, deps: TaskApprovalDeps
    ) -> ApprovalHandlerResult:
        deps.constraints._apply_task_scheduling_constraint_decision(
            task_id=request.payload["task_id"],
            constraint_type=coerce_constraint_type(request.payload.get("constraint_type")),
            constraint_date=_as_optional_date(request.payload.get("constraint_date")),
            expected_version=request.payload.get("expected_version"),
        )
        return ApprovalHandlerResult(
            domain_events=deps.uow_scope.take_pending_events()
        )

    def apply_resource_leveling_plan(
        self, request: ApprovalRequest, deps: TaskApprovalDeps
    ) -> ApprovalHandlerResult:
        deps.leveling._apply_resource_leveling_plan_decision(
            project_id=request.project_id,
            moves=request.payload["moves"],
            schedule_fingerprint=request.payload["schedule_fingerprint"],
        )
        return ApprovalHandlerResult(
            domain_events=deps.uow_scope.take_pending_events()
        )


__all__ = ["TaskApprovalDeps", "TaskApprovalParticipant"]
