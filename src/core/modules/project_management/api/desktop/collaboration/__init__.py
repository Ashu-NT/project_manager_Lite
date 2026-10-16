"""Collaboration desktop API — domain-based package."""

from src.core.modules.project_management.api.desktop.collaboration.api import (
    ProjectManagementCollaborationDesktopApi,
)
from src.core.modules.project_management.api.desktop.collaboration.factories.collaboration_factory import (
    build_project_management_collaboration_desktop_api,
)

__all__ = [
    "ProjectManagementCollaborationDesktopApi",
    "build_project_management_collaboration_desktop_api",
]
