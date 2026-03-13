"""Dependency dialogs facade.

Keep imports stable while concrete dialogs stay in focused modules.
"""

from .dependency_add_dialog import DependencyAddDialog
from .dependency_list_dialog import DependencyListDialog
from .dependency_shared import dependency_direction as _dependency_direction

__all__ = ["DependencyAddDialog", "DependencyListDialog", "_dependency_direction"]
