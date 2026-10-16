"""Projects desktop API — modular enterprise package."""

from src.core.modules.project_management.api.desktop.projects.api import (
    ProjectManagementProjectsDesktopApi,
)
from src.core.modules.project_management.api.desktop.projects.factories.projects_api_factory import (
    build_project_management_projects_desktop_api,
)
from src.core.modules.project_management.application.projects.dto.commands.project_lifecycle import (
    ProjectCreateCommand,
    ProjectUpdateCommand,
)
from src.core.modules.project_management.application.projects.dto.commands.project_resources import (
    ProjectResourceAssignCommand,
    ProjectResourceUpdateCommand,
)

__all__ = ['ProjectCreateCommand', 'ProjectManagementProjectsDesktopApi', 'ProjectResourceAssignCommand', 'ProjectResourceUpdateCommand', 'ProjectUpdateCommand', 'build_project_management_projects_desktop_api']
