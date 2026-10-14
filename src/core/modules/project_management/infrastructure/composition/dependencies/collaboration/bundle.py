"""collaboration composition dependencies."""
from __future__ import annotations

from dataclasses import dataclass

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


@dataclass(frozen=True)
class CollaborationComposition:
    comment_commands: CollaborationCommentCommandHandler
    comment_engagement: CollaborationCommentEngagementHandler
    presence_commands: CollaborationPresenceCommandHandler
    comment_query: CollaborationCommentQueryHandler
    document_query: CollaborationDocumentQueryHandler
    inbox_query: CollaborationInboxQueryHandler
    presence_query: CollaborationPresenceQueryHandler
