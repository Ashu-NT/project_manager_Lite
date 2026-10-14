"""Collaboration desktop API — domain-based package."""

from src.core.modules.project_management.api.desktop.collaboration.api import (
    ProjectManagementCollaborationDesktopApi,
)
from src.core.modules.project_management.api.desktop.collaboration.factories.collaboration_factory import (
    build_project_management_collaboration_desktop_api,
)
from src.core.modules.project_management.api.desktop.collaboration.models.collaboration_models import (
    CollaborationCommentPageDto,
    CollaborationContextOptionsDto,
    CollaborationInboxDesktopDto,
    CollaborationPresenceDesktopDto,
    TaskCollaborationCommentDesktopDto,
    TaskCollaborationDocumentOptionDescriptor,
    TaskCollaborationMentionOptionDescriptor,
    TaskCollaborationReactionSummaryDto,
    TaskCollaborationSnapshotDto,
)
from src.core.modules.project_management.application.collaboration.dto import (
    TaskCollaborationDeleteCommand,
    TaskCollaborationEditCommand,
    TaskCollaborationPostCommand,
    TaskCollaborationReactionCommand,
)

__all__ = [
    "CollaborationCommentPageDto",
    "CollaborationContextOptionsDto",
    "CollaborationInboxDesktopDto",
    "CollaborationPresenceDesktopDto",
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
