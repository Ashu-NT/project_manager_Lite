"""Project dialog facade.

Keep imports stable while implementations live in focused modules.
"""

from .project_edit_dialog import ProjectEditDialog
from .project_resource_edit_dialog import ProjectResourceEditDialog

__all__ = [
    "ProjectEditDialog",
    "ProjectResourceEditDialog",
]
