"""Factory for building the collaboration desktop API."""

from __future__ import annotations

from src.core.modules.project_management.application.collaboration import CollaborationService
from src.core.modules.project_management.api.desktop.collaboration.api import (
    ProjectManagementCollaborationDesktopApi,
)


def build_project_management_collaboration_desktop_api(
    *,
    collaboration_service: CollaborationService | None = None,
) -> ProjectManagementCollaborationDesktopApi:
    return ProjectManagementCollaborationDesktopApi(
        collaboration_service=collaboration_service,
    )


__all__ = ["build_project_management_collaboration_desktop_api"]
