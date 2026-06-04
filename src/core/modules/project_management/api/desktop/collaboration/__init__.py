"""Collaboration desktop API — domain-based package."""

from src.core.modules.project_management.api.desktop.collaboration.api import (
    ProjectManagementCollaborationDesktopApi,
)
from src.core.modules.project_management.api.desktop.collaboration.commands.task_commands import (
    TaskCollaborationPostCommand,
)
from src.core.modules.project_management.api.desktop.collaboration.factories.collaboration_factory import (
    build_project_management_collaboration_desktop_api,
)
from src.core.modules.project_management.api.desktop.collaboration.models.collaboration_models import (
    CollaborationInboxDesktopDto,
    CollaborationNotificationDesktopDto,
    CollaborationPresenceDesktopDto,
    CollaborationWorkspaceSnapshotDto,
    TaskCollaborationCommentDesktopDto,
    TaskCollaborationDocumentOptionDescriptor,
    TaskCollaborationMentionOptionDescriptor,
    TaskCollaborationSnapshotDto,
)

__all__ = [
    "CollaborationInboxDesktopDto",
    "CollaborationNotificationDesktopDto",
    "CollaborationPresenceDesktopDto",
    "CollaborationWorkspaceSnapshotDto",
    "ProjectManagementCollaborationDesktopApi",
    "TaskCollaborationCommentDesktopDto",
    "TaskCollaborationDocumentOptionDescriptor",
    "TaskCollaborationMentionOptionDescriptor",
    "TaskCollaborationPostCommand",
    "TaskCollaborationSnapshotDto",
    "build_project_management_collaboration_desktop_api",
]
