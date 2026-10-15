"""Task use-case commands."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskWbsMoveCommand:
    task_id: str
    parent_task_id: str | None
    wbs_code: str | None = None
    sort_order: int | None = None
    expected_version: int | None = None


__all__ = ["TaskWbsMoveCommand"]
