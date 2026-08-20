"""Shared resource leveling DTOs."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class ResourceConflictEntry:
    task_id: str
    task_name: str
    allocation_percent: float


@dataclass
class ResourceConflict:
    resource_id: str
    resource_name: str
    conflict_date: date
    total_allocation_percent: float
    entries: list[ResourceConflictEntry]


# ── R4.4K: pure, in-memory leveling proposal (Preview never persists) ──


@dataclass(frozen=True)
class ProposedTaskMove:
    """One task's proposed resource-driven placement, with enough facts
    for the Leveling Inspector to explain WHY without QML recalculating
    anything (R4.4S) -- float/criticality/infeasibility are copied
    verbatim from the canonical CPMTaskInfo before/after this move was
    layered into the in-memory schedule, never re-derived."""

    task_id: str
    task_name: str
    wbs_code: str
    old_start: date
    old_finish: date
    new_start: date
    new_finish: date
    shift_working_days: int
    reason: str
    resource_ids: tuple[str, ...]
    resource_names: tuple[str, ...]
    float_before: int | None
    float_after: int | None
    critical_before: bool
    critical_after: bool
    infeasible_after: bool
    deadline_warning: str = ""


@dataclass(frozen=True)
class UnresolvedConflict:
    """A resource overload the planner could not legally resolve --
    surfaced explicitly (R4.4T), never silently dropped."""

    resource_id: str
    resource_name: str
    conflict_date: date
    total_allocation_percent: float
    reason: str


@dataclass(frozen=True)
class LevelingProposal:
    """The one typed, application-level preview result (R4.4K).
    Read-only by construction -- nothing in this module or its consumer
    writes to a repository or increments a version. ``schedule_
    fingerprint`` is the staleness token Apply must revalidate (R4.4L)."""

    project_id: str
    schedule_fingerprint: str
    is_feasible: bool
    resource_conflicts_before: int
    resource_conflicts_after: int
    moves: tuple[ProposedTaskMove, ...]
    unresolved_conflicts: tuple[UnresolvedConflict, ...]
    project_finish_before: date | None
    project_finish_after: date | None
    critical_path_changed: bool
    new_infeasibility_task_ids: tuple[str, ...]
    warnings: tuple[str, ...]


__all__ = [
    "ResourceConflict",
    "ResourceConflictEntry",
    "ProposedTaskMove",
    "UnresolvedConflict",
    "LevelingProposal",
]
