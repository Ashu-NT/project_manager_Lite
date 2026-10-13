"""Projects desktop API — modular enterprise package."""

from src.core.modules.project_management.api.desktop.projects.api import (
    ProjectManagementProjectsDesktopApi,
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
    ProjectResourceUsageDesktopDto,
    ProjectStatusDescriptor,
)
from src.core.modules.project_management.contracts.use_cases.projects import (
    ProjectCreateCommand,
    ProjectUpdateCommand,
)

__all__ = [
    "ProjectAssignableResourceOptionDescriptor",
    "ProjectCreateCommand",
    "ProjectDesktopDto",
    "ProjectManagementProjectsDesktopApi",
    "ProjectResourceAssignCommand",
    "ProjectResourceDesktopDto",
    "ProjectResourceUpdateCommand",
    "ProjectResourceUsageDesktopDto",
    "ProjectStatusDescriptor",
    "ProjectUpdateCommand",
    "build_project_management_projects_desktop_api",
]
