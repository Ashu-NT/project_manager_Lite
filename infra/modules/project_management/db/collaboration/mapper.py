from __future__ import annotations

import json

from core.modules.project_management.domain.collaboration import TaskComment, TaskPresence
from src.infra.persistence.orm.project_management.models import TaskCommentORM, TaskPresenceORM


def task_comment_to_orm(comment: TaskComment) -> TaskCommentORM:
    return TaskCommentORM(
        id=comment.id,
        task_id=comment.task_id,
        author_user_id=comment.author_user_id,
        author_username=comment.author_username,
        body=comment.body,
        mentions_json=json.dumps(list(comment.mentions or [])),
        mentioned_user_ids_json=json.dumps(list(comment.mentioned_user_ids or [])),
        attachments_json=json.dumps(list(comment.attachments or [])),
        read_by_json=json.dumps(list(comment.read_by or [])),
        read_by_user_ids_json=json.dumps(list(comment.read_by_user_ids or [])),
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
        mentioned_user_ids=[item for item in _decode(obj.mentioned_user_ids_json)],
        attachments=_decode(obj.attachments_json),
        read_by=[item.lower() for item in _decode(obj.read_by_json)],
        read_by_user_ids=[item for item in _decode(obj.read_by_user_ids_json)],
        created_at=obj.created_at,
    )


def task_presence_to_orm(presence: TaskPresence) -> TaskPresenceORM:
    return TaskPresenceORM(
        id=presence.id,
        task_id=presence.task_id,
        user_id=presence.user_id,
        username=presence.username,
        display_name=presence.display_name,
        activity=presence.activity,
        started_at=presence.started_at,
        last_seen_at=presence.last_seen_at,
    )


def task_presence_from_orm(obj: TaskPresenceORM) -> TaskPresence:
    return TaskPresence(
        id=obj.id,
        task_id=obj.task_id,
        user_id=obj.user_id,
        username=obj.username,
        display_name=obj.display_name,
        activity=obj.activity,
        started_at=obj.started_at,
        last_seen_at=obj.last_seen_at,
    )


__all__ = [
    "task_comment_from_orm",
    "task_comment_to_orm",
    "task_presence_from_orm",
    "task_presence_to_orm",
]
