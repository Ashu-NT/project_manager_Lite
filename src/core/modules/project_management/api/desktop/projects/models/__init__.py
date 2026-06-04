"""Projects desktop DTO models."""

from src.core.modules.project_management.api.desktop.projects.models.project import (
    ProjectDesktopDto,
    ProjectStatusDescriptor,
)
from src.core.modules.project_management.api.desktop.projects.models.resources import (
    ProjectAssignableResourceOptionDescriptor,
    ProjectResourceDesktopDto,
)

__all__ = [
    "ProjectAssignableResourceOptionDescriptor",
    "ProjectDesktopDto",
    "ProjectResourceDesktopDto",
    "ProjectStatusDescriptor",
]
