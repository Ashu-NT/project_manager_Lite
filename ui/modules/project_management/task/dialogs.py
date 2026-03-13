"""Task dialog facade.

Keep external imports stable while dialog implementations live in bounded
modules (`task_dialogs`, `dependency_dialogs`, `assignment_dialogs`).
"""

from .assignment_dialogs import AssignmentAddDialog, AssignmentListDialog
from .dependency_dialogs import DependencyAddDialog, DependencyListDialog
from .task_dialogs import TaskEditDialog, TaskProgressDialog

__all__ = [
    "TaskEditDialog",
    "TaskProgressDialog",
    "DependencyAddDialog",
    "DependencyListDialog",
    "AssignmentAddDialog",
    "AssignmentListDialog",
]
