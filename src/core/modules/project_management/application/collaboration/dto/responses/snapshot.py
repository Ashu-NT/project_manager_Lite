from __future__ import annotations

from dataclasses import dataclass, field

from src.core.modules.project_management.application.collaboration.dto.responses.comments import (
    TaskCommentActionContext,
)
from src.core.modules.project_management.contracts.reads.collaboration.models.workspace_facts import (
    TaskDetailCommentFact,
    TaskDetailLinkedDocumentFact,
    TaskDocumentOptionFact,
)
from src.core.modules.project_management.domain.collaboration import (
    CollaborationMentionCandidate,
    TaskPresenceStatusItem,
)


@dataclass(frozen=True)
class TaskCollaborationSnapshotResponse:
    available: bool = False
    comments: tuple[TaskDetailCommentFact, ...] = ()
    active_presence: tuple[TaskPresenceStatusItem, ...] = ()
    mention_candidates: tuple[CollaborationMentionCandidate, ...] = ()
    documents: tuple[TaskDocumentOptionFact, ...] = ()
    linked_documents: dict[str, tuple[TaskDetailLinkedDocumentFact, ...]] = field(
        default_factory=dict
    )
    action_context: TaskCommentActionContext = TaskCommentActionContext(
        "", False, False
    )
    comment_total: int = 0
    comment_page: int = 1
    comment_page_size: int = 25
