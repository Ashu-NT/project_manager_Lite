"""Projects desktop DTO models."""

from src.core.modules.project_management.api.desktop.projects.models.project import (
    ProjectCatalogPageDesktopDto,
    ProjectDesktopDto,
    ProjectStatusDescriptor,
)
from src.core.modules.project_management.api.desktop.projects.models.resources import (
    ProjectAssignableResourceOptionDescriptor,
    ProjectResourceDesktopDto,
    ProjectResourceUsageDesktopDto,
)

__all__ = [
    "ProjectAssignableResourceOptionDescriptor",
    "ProjectCatalogPageDesktopDto",
    "ProjectDesktopDto",
    "ProjectResourceDesktopDto",
    "ProjectResourceUsageDesktopDto",
    "ProjectStatusDescriptor",
]
