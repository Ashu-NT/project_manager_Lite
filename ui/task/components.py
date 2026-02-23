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
from .assignment_models import AssignmentTableModel
from .models import TaskTableModel

__all__ = [
    "TaskTableModel",
    "AssignmentTableModel",
    "TaskEditDialog",
    "TaskProgressDialog",
    "DependencyAddDialog",
    "DependencyListDialog",
    "AssignmentAddDialog",
    "AssignmentListDialog",
]
