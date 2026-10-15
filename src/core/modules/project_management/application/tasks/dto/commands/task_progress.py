"""Task use-case commands."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class TaskProgressCommand:
    task_id: str
    percent_complete: float | None = None
    actual_start: date | None = None
    actual_end: date | None = None
    status: str | None = None
    expected_version: int | None = None


@dataclass(frozen=True)
class TaskBulkStatusCommand:
    task_ids: tuple[str, ...]
    status: str
    reopen_percent_complete: float | None = None


__all__ = ["TaskProgressCommand", "TaskBulkStatusCommand"]
