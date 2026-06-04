from dataclasses import dataclass


@dataclass(frozen=True)
class SchedulingChangeImpactAffectedTaskDto:
    task_id: str
    task_name: str
    start_shift_days: int
    finish_shift_days: int
    is_critical: bool


@dataclass(frozen=True)
class SchedulingChangeImpactDto:
    task_id: str
    affected_count: int
    max_project_finish_shift_days: int
    requires_approval: bool
    newly_critical_count: int
    no_longer_critical_count: int
    affected_tasks: tuple[SchedulingChangeImpactAffectedTaskDto, ...]


__all__ = ["SchedulingChangeImpactAffectedTaskDto", "SchedulingChangeImpactDto"]
