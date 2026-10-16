"""Collaboration desktop API — domain-based package."""

from src.core.modules.project_management.api.desktop.collaboration.api import (
    ProjectManagementCollaborationDesktopApi,
)
from src.core.modules.project_management.api.desktop.collaboration.factories.collaboration_factory import (
    build_project_management_collaboration_desktop_api,
)
from src.core.modules.project_management.api.desktop.collaboration.models.collaboration_models import (
    CollaborationCommentPageDto,
    CollaborationInboxDesktopDto,
    CollaborationPresenceDesktopDto,
    TaskCollaborationCommentDesktopDto,
    TaskCollaborationDocumentOptionDescriptor,
    TaskCollaborationMentionOptionDescriptor,
    TaskCollaborationSnapshotDto,
)

__all__ = ['CollaborationCommentPageDto', 'CollaborationInboxDesktopDto', 'CollaborationPresenceDesktopDto', 'ProjectManagementCollaborationDesktopApi', 'TaskCollaborationCommentDesktopDto', 'TaskCollaborationDocumentOptionDescriptor', 'TaskCollaborationMentionOptionDescriptor', 'TaskCollaborationSnapshotDto', 'build_project_management_collaboration_desktop_api']
