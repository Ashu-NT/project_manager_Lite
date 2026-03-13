from __future__ import annotations

import json

from core.models import TaskComment
from infra.db.models import TaskCommentORM


def task_comment_to_orm(comment: TaskComment) -> TaskCommentORM:
    return TaskCommentORM(
        id=comment.id,
        task_id=comment.task_id,
        author_user_id=comment.author_user_id,
        author_username=comment.author_username,
        body=comment.body,
        mentions_json=json.dumps(list(comment.mentions or [])),
        attachments_json=json.dumps(list(comment.attachments or [])),
        read_by_json=json.dumps(list(comment.read_by or [])),
        created_at=comment.created_at,
    )


def task_comment_from_orm(obj: TaskCommentORM) -> TaskComment:
    def _decode(value: str | None) -> list[str]:
        try:
            data = json.loads(value or "[]")
        except Exception:
            return []
        if not isinstance(data, list):
            return []
        return [str(item).strip() for item in data if str(item).strip()]

    return TaskComment(
        id=obj.id,
        task_id=obj.task_id,
        author_user_id=obj.author_user_id,
        author_username=obj.author_username,
        body=obj.body,
        mentions=[item.lower() for item in _decode(obj.mentions_json)],
        attachments=_decode(obj.attachments_json),
        read_by=[item.lower() for item in _decode(obj.read_by_json)],
        created_at=obj.created_at,
    )


__all__ = ["task_comment_from_orm", "task_comment_to_orm"]
