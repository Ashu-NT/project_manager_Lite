from __future__ import annotations

from src.core.modules.project_management.domain.enums import TaskStatus


def coerce_task_status(value: str | TaskStatus | None) -> TaskStatus:
    if isinstance(value, TaskStatus):
        return value
    normalized_value = str(value or TaskStatus.TODO.value).strip().upper()
    try:
        return TaskStatus(normalized_value)
    except ValueError as exc:
        raise ValueError(f"Unsupported task status: {normalized_value}.") from exc


__all__ = ["coerce_task_status"]
