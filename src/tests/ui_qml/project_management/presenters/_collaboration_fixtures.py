from dataclasses import fields
from types import SimpleNamespace

from src.core.modules.project_management.application.collaboration.dto.responses.comments import TaskCommentResponseDto
from src.core.modules.project_management.application.collaboration.mappers.collaboration import map_reactions
from src.core.modules.project_management.contracts.reads.collaboration.models.workspace_facts import TaskDetailCommentFact, TaskDetailCommentReadPage


def comment_fact(comment: SimpleNamespace) -> TaskDetailCommentFact:
    data = vars(comment)
    return TaskDetailCommentFact(
        id=comment.id,
        task_id=comment.task_id,
        author_user_id=data.get("author_user_id"),
        author_username=comment.author_username,
        body=comment.body,
        mentions=tuple(comment.mentions),
        attachments=tuple(comment.attachments),
        created_at=comment.created_at,
        parent_comment_id=data.get("parent_comment_id"),
        parent_author_username=data.get("parent_author_username", ""),
        reply_count=data.get("reply_count", 0),
        updated_at=data.get("updated_at"),
        deleted_at=data.get("deleted_at"),
        deletion_reason=data.get("deletion_reason"),
        reactions=tuple((emoji, tuple(users)) for emoji, users in data.get("reactions", {}).items()),
        version=data.get("version", 1),
    )


def comment_page(comments, task_id: str, *, page: int, page_size: int) -> TaskDetailCommentReadPage:
    rows = [comment_fact(comment) for comment in comments if comment.task_id == task_id]
    start = (page - 1) * page_size
    return TaskDetailCommentReadPage(tuple(rows[start:start + page_size]), len(rows), page, page_size)


def comment_response(comment: SimpleNamespace) -> TaskCommentResponseDto:
    fact = comment_fact(comment)
    values = {field.name: getattr(fact, field.name) for field in fields(TaskCommentResponseDto) if field.name != "reactions"}
    return TaskCommentResponseDto(**values, reactions=map_reactions(dict(fact.reactions), principal_user_id="user-alex"))
