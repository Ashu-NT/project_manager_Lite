from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskBulkStatusCommand:
    task_ids: tuple[str, ...]
    status: str
    reopen_percent_complete: float | None = None


__all__ = ["TaskBulkStatusCommand"]
