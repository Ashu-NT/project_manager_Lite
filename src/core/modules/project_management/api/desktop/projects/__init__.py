"""Projects desktop API — modular enterprise package."""

from src.core.modules.project_management.api.desktop.projects.api import (
    ProjectManagementProjectsDesktopApi,
)
from src.core.modules.project_management.api.desktop.projects.commands.project_commands import (
    ProjectCreateCommand,
    ProjectUpdateCommand,
)
from src.core.modules.project_management.api.desktop.projects.commands.resource_commands import (
    ProjectResourceAssignCommand,
    ProjectResourceUpdateCommand,
)
from src.core.modules.project_management.api.desktop.projects.factories.projects_api_factory import (
    build_project_management_projects_desktop_api,
)
from src.core.modules.project_management.api.desktop.projects.models import (
    ProjectAssignableResourceOptionDescriptor,
    ProjectDesktopDto,
    ProjectResourceDesktopDto,
    ProjectStatusDescriptor,
)

__all__ = [
    "ProjectAssignableResourceOptionDescriptor",
    "ProjectCreateCommand",
    "ProjectDesktopDto",
    "ProjectManagementProjectsDesktopApi",
    "ProjectResourceAssignCommand",
    "ProjectResourceDesktopDto",
    "ProjectResourceUpdateCommand",
    "ProjectStatusDescriptor",
    "ProjectUpdateCommand",
    "build_project_management_projects_desktop_api",
]
