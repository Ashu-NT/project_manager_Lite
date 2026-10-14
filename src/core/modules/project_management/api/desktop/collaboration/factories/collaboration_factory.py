"""Factory for building the collaboration desktop API."""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.collaboration.api import (
    ProjectManagementCollaborationDesktopApi,
)
from src.core.modules.project_management.application.collaboration.commands import (
    CollaborationCommentCommandHandler,
    CollaborationCommentEngagementHandler,
    CollaborationPresenceCommandHandler,
)
from src.core.modules.project_management.application.collaboration.queries import (
    CollaborationCommentQueryHandler,
    CollaborationDocumentQueryHandler,
    CollaborationInboxQueryHandler,
    CollaborationPresenceQueryHandler,
)


def build_project_management_collaboration_desktop_api(
    *,
    inbox_query: CollaborationInboxQueryHandler | None = None,
    comment_query: CollaborationCommentQueryHandler | None = None,
    document_query: CollaborationDocumentQueryHandler | None = None,
    presence_query: CollaborationPresenceQueryHandler | None = None,
    comment_commands: CollaborationCommentCommandHandler | None = None,
    comment_engagement: CollaborationCommentEngagementHandler | None = None,
    presence_commands: CollaborationPresenceCommandHandler | None = None,
) -> ProjectManagementCollaborationDesktopApi:
    return ProjectManagementCollaborationDesktopApi(
        inbox_query=inbox_query,
        comment_query=comment_query,
        document_query=document_query,
        presence_query=presence_query,
        comment_commands=comment_commands,
        comment_engagement=comment_engagement,
        presence_commands=presence_commands,
    )


__all__ = ["build_project_management_collaboration_desktop_api"]
