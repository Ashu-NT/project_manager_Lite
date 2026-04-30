from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from src.core.modules.project_management.domain.collaboration import TaskPresenceStatusItem
from src.core.modules.project_management.application.tasks import CollaborationService


@contextmanager
def task_presence_session(
    collaboration_service: CollaborationService | None,
    *,
    task_id: str,
    activity: str,
) -> Iterator[None]:
    if collaboration_service is None:
        yield
        return
    try:
        collaboration_service.touch_task_presence(task_id, activity=activity)
    except Exception:
        pass
    try:
        yield
    finally:
        try:
            collaboration_service.clear_task_presence(task_id)
        except Exception:
            pass


def format_presence_lines(
    rows: list[TaskPresenceStatusItem],
    *,
    include_self: bool = False,
) -> list[str]:
    visible = [row for row in rows if include_self or not row.is_self]
    if not visible:
        return []
    lines: list[str] = []
    for row in visible:
        label = row.display_name or f"@{row.username}"
        if row.display_name and row.username:
            label = f"{row.display_name} (@{row.username})"
        lines.append(f"{label}: {row.activity.replace('_', ' ')}")
    return lines


__all__ = ["format_presence_lines", "task_presence_session"]
