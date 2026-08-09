from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.tasks import (
    TaskSelectorOptionViewModel,
)


def build_task_priority_options() -> tuple[TaskSelectorOptionViewModel, ...]:
    return (
        TaskSelectorOptionViewModel(value="all", label="All priorities"),
        TaskSelectorOptionViewModel(value="high", label="High (>= 70)"),
        TaskSelectorOptionViewModel(value="medium", label="Medium (30-69)"),
        TaskSelectorOptionViewModel(value="low", label="Low (< 30)"),
    )


def build_task_schedule_options() -> tuple[TaskSelectorOptionViewModel, ...]:
    return (
        TaskSelectorOptionViewModel(value="all", label="All schedule states"),
        TaskSelectorOptionViewModel(value="overdue", label="Overdue"),
        TaskSelectorOptionViewModel(value="due_7", label="Due 7 days"),
        TaskSelectorOptionViewModel(value="no_deadline", label="No deadline"),
    )


def normalize_task_filter(
    value: str,
    options: tuple[TaskSelectorOptionViewModel, ...],
    *,
    default_value: str = "all",
) -> str:
    normalized_value = (value or default_value).strip().lower()
    available_values = {
        option.value.lower(): option.value
        for option in options
    }
    return available_values.get(normalized_value, default_value)


__all__ = [
    "build_task_priority_options",
    "build_task_schedule_options",
    "normalize_task_filter",
]
