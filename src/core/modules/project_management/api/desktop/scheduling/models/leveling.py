from dataclasses import dataclass


@dataclass(frozen=True)
class SchedulingProposedTaskMoveDto:
    task_id: str
    task_name: str
    wbs_code: str
    old_start: str
    old_start_label: str
    old_finish_label: str
    new_start: str
    new_start_label: str
    new_finish_label: str
    shift_working_days: int
    reason: str
    resource_names_label: str
    float_before: int | None
    float_after: int | None
    critical_before: bool
    critical_after: bool
    infeasible_after: bool
    deadline_warning: str


@dataclass(frozen=True)
class SchedulingUnresolvedConflictDto:
    resource_id: str
    resource_name: str
    conflict_date_label: str
    total_allocation_percent: float
    total_allocation_label: str
    reason: str


@dataclass(frozen=True)
class SchedulingLevelingProposalDto:
    project_id: str
    schedule_fingerprint: str
    is_feasible: bool
    resource_conflicts_before: int
    resource_conflicts_after: int
    moves: tuple[SchedulingProposedTaskMoveDto, ...]
    unresolved_conflicts: tuple[SchedulingUnresolvedConflictDto, ...]
    project_finish_before_label: str
    project_finish_after_label: str
    critical_path_changed: bool
    warnings: tuple[str, ...]


__all__ = [
    "SchedulingProposedTaskMoveDto",
    "SchedulingUnresolvedConflictDto",
    "SchedulingLevelingProposalDto",
]
