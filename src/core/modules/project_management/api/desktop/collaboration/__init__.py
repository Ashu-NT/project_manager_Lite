"""Collaboration desktop API — domain-based package."""

from src.core.modules.project_management.api.desktop.collaboration.api import (
    ProjectManagementCollaborationDesktopApi,
)
from src.core.modules.project_management.api.desktop.collaboration.commands.task_commands import (
    TaskCollaborationDeleteCommand,
    TaskCollaborationEditCommand,
    TaskCollaborationPostCommand,
    TaskCollaborationReactionCommand,
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
    TaskCollaborationReactionSummaryDto,
    TaskCollaborationSnapshotDto,
)

__all__ = [
    "CollaborationInboxDesktopDto",
    "CollaborationNotificationDesktopDto",
    "CollaborationPresenceDesktopDto",
    "CollaborationWorkspaceSnapshotDto",
    "ProjectManagementCollaborationDesktopApi",
    "TaskCollaborationCommentDesktopDto",
    "TaskCollaborationDeleteCommand",
    "TaskCollaborationDocumentOptionDescriptor",
    "TaskCollaborationEditCommand",
    "TaskCollaborationMentionOptionDescriptor",
    "TaskCollaborationPostCommand",
    "TaskCollaborationReactionCommand",
    "TaskCollaborationReactionSummaryDto",
    "TaskCollaborationSnapshotDto",
    "build_project_management_collaboration_desktop_api",
]
