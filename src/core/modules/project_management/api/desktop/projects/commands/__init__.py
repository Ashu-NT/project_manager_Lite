"""Projects desktop commands."""

from src.core.modules.project_management.api.desktop.projects.commands.project_commands import (
    ProjectCreateCommand,
    ProjectUpdateCommand,
)
from src.core.modules.project_management.api.desktop.projects.commands.resource_commands import (
    ProjectResourceAssignCommand,
    ProjectResourceUpdateCommand,
)

__all__ = [
    "ProjectCreateCommand",
    "ProjectResourceAssignCommand",
    "ProjectResourceUpdateCommand",
    "ProjectUpdateCommand",
]
