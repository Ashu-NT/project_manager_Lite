"""R4.4G -- documented target movability policy for automatic resource
leveling. One function, `task_movability`, is the single place this
policy is encoded; the planner (`resource_leveling_planner.py`) never
re-derives constraint semantics itself, it only asks this module
whether a task may be considered as a leveling candidate and, if so,
what ceiling (if any) bounds how far it may move.

Policy (see R4_4_PLANNING_SCHEDULING_IMPLEMENTATION_SUMMARY.md,
"Movability policy," for the product rationale):

- No constraint (ASAP): movable, no ceiling.
- START_NO_EARLIER_THAN / FINISH_NO_EARLIER_THAN (floors): movable --
  the user's own floor already composes with any resource-leveling
  floor via max() in the forward pass (task_date_math.py); leveling
  does not need to treat these specially beyond that composition.
- START_NO_LATER_THAN: movable, but the proposed start must not exceed
  the constraint date -- a ceiling, never silently violated.
- FINISH_NO_LATER_THAN: movable, but the proposed finish must not
  exceed the constraint date -- a ceiling.
- MUST_START_ON / MUST_FINISH_ON (exact pins): NOT movable by automatic
  leveling. A pin represents an exact, user-mandated date; leveling
  must resolve overloads by moving a DIFFERENT task, never this one.
- Deadline (task.deadline, independent of constraint_type): movable,
  but a proposed placement that pushes the finish past the deadline
  must surface an explicit warning on the proposal -- never silently
  hidden.
- Actual-date locked (actual_start or actual_end set): NOT movable --
  historical/in-progress execution facts, never a leveling candidate.
- Already-infeasible-by-dependency/constraint (CPMTaskInfo.is_infeasible
  BEFORE any leveling move): leveling may attempt to resolve a
  resource-driven overload for such a task, but must never be the
  cause of NEW infeasibility beyond what already existed -- enforced by
  the planner re-checking is_infeasible after each candidate, not by
  this policy module (which only answers "is this task a legal
  leveling candidate at all," not "is a specific candidate date safe").

ALAP does not exist in this codebase and is deliberately not
implemented here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.core.modules.project_management.domain.enums import ConstraintType
from src.core.modules.project_management.domain.tasks.task import Task


@dataclass(frozen=True, slots=True)
class MovabilityDecision:
    movable: bool
    reason: str
    # The latest legal start/finish this task's OWN ceiling constraint
    # allows, if any -- None means no ceiling from constraint_type.
    start_ceiling: date | None = None
    finish_ceiling: date | None = None
    # True when task.deadline exists and must be reported as a warning
    # if a candidate placement would push the finish past it -- never a
    # hard block, per the documented policy above.
    deadline: date | None = None


def _coerce_constraint_type(task: Task) -> ConstraintType | None:
    raw = getattr(task, "constraint_type", None)
    if raw is None:
        return None
    if isinstance(raw, ConstraintType):
        return raw
    try:
        return ConstraintType(str(raw))
    except ValueError:
        return None


def task_movability(task: Task) -> MovabilityDecision:
    """Single source of truth for whether automatic leveling may
    consider `task` as a candidate to move, and what ceiling (if any)
    bounds the move. Does not consult dependencies/successors or
    resource facts at all -- those are the planner's job, layered on
    top of this task-intrinsic policy."""
    if getattr(task, "actual_start", None) is not None or getattr(task, "actual_end", None) is not None:
        return MovabilityDecision(movable=False, reason="actual_date_locked")

    ct = _coerce_constraint_type(task)
    deadline = getattr(task, "deadline", None)

    if ct == ConstraintType.MUST_START_ON:
        return MovabilityDecision(movable=False, reason="exact_pin_must_start_on")
    if ct == ConstraintType.MUST_FINISH_ON:
        return MovabilityDecision(movable=False, reason="exact_pin_must_finish_on")

    start_ceiling = getattr(task, "constraint_date", None) if ct == ConstraintType.START_NO_LATER_THAN else None
    finish_ceiling = getattr(task, "constraint_date", None) if ct == ConstraintType.FINISH_NO_LATER_THAN else None

    return MovabilityDecision(
        movable=True,
        reason="movable",
        start_ceiling=start_ceiling,
        finish_ceiling=finish_ceiling,
        deadline=deadline,
    )


__all__ = ["MovabilityDecision", "task_movability"]
