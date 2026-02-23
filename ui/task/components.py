"""Compatibility exports for legacy imports.

Prefer importing from ``ui.task.models`` and ``ui.task.dialogs`` directly.
"""

from .dialogs import (
    AssignmentAddDialog,
    AssignmentListDialog,
    DependencyAddDialog,
    DependencyListDialog,
    TaskEditDialog,
    TaskProgressDialog,
)
from .models import TaskTableModel

__all__ = [
    "TaskTableModel",
    "TaskEditDialog",
    "TaskProgressDialog",
    "DependencyAddDialog",
    "DependencyListDialog",
    "AssignmentAddDialog",
    "AssignmentListDialog",
]
