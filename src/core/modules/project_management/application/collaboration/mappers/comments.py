"""Map persisted comment state and reader facts into discussion responses."""

from src.core.modules.project_management.application.collaboration.dto.responses.comments import (
    TaskCommentResponseDto,
)
from src.core.modules.project_management.application.collaboration.mappers.collaboration import (
    map_reactions,
)
from src.core.modules.project_management.domain.collaboration import TaskComment


def map_comment(
    comment: TaskComment, *, principal_user_id: str
) -> TaskCommentResponseDto:
    reactions = (
        dict(comment.reactions)
        if isinstance(comment.reactions, tuple)
        else comment.reactions
    )
    return TaskCommentResponseDto(
        id=comment.id,
        task_id=comment.task_id,
        author_user_id=comment.author_user_id,
        author_username=comment.author_username,
        body=comment.body,
        mentions=tuple(comment.mentions),
        attachments=tuple(comment.attachments),
        created_at=comment.created_at,
        parent_comment_id=comment.parent_comment_id,
        updated_at=comment.updated_at,
        deleted_at=comment.deleted_at,
        deletion_reason=comment.deletion_reason,
        reactions=map_reactions(
            {} if comment.deleted_at else reactions, principal_user_id=principal_user_id
        ),
        version=comment.version,
        parent_author_username="",
        reply_count=0,
    )
