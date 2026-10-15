"""Task use-case commands."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class TaskConstraintUpdateCommand:
    """Set/clear a Task's scheduling constraint. constraint_type="" (or
    None) means ASAP -- clears both fields back to no explicit
    constraint. Deliberately separate from TaskUpdateCommand: this is a
    schedule-affecting, governed mutation (see
    TaskSchedulingConstraintHandler), not a generic field edit."""

    task_id: str
    constraint_type: str | None = None
    constraint_date: date | None = None
    expected_version: int | None = None


__all__ = ["TaskConstraintUpdateCommand"]
