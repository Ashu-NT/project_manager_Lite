from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from src.core.modules.project_management.domain.tasks.task import Task


@dataclass(frozen=True, slots=True)
class ApprovedTaskScheduleChange:
    reference_id: str
    project_id: str
    task_id: str
    expected_version: int
    start_date: date | None
    finish_date: date | None


@dataclass(frozen=True, slots=True)
class AppliedTaskScheduleChange:
    reference_id: str
    task_id: str
    version: int
    start_date: date
    finish_date: date


class ApprovedScheduleChangePort(Protocol):
    def _validate_approved_schedule_changes(
        self, changes: list[ApprovedTaskScheduleChange]
    ) -> list[tuple[ApprovedTaskScheduleChange, Task]]: ...

    def _apply_approved_schedule_changes(
        self,
        changes: list[ApprovedTaskScheduleChange],
        *,
        actor_id: str,
        commit: bool = False,
    ) -> list[AppliedTaskScheduleChange]: ...


__all__ = [
    "AppliedTaskScheduleChange",
    "ApprovedScheduleChangePort",
    "ApprovedTaskScheduleChange",
]
