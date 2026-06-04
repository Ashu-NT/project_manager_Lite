from __future__ import annotations

from src.core.modules.project_management.api.desktop.tasks.models.options import (
    TaskStatusDescriptor,
)
from src.core.modules.project_management.domain.enums import TaskStatus


def build_status_options() -> tuple[TaskStatusDescriptor, ...]:
    return tuple(
        TaskStatusDescriptor(
            value=status.value,
            label=status.value.replace("_", " ").title(),
        )
        for status in TaskStatus
    )


__all__ = ["build_status_options"]
