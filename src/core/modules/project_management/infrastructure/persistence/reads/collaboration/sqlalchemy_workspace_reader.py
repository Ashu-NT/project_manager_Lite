from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.reads.collaboration.models.workspace_facts import (
    CollaborationCommentFact,
    CollaborationPresenceFact,
    CollaborationWorkspaceFacts,
)
from src.core.modules.project_management.infrastructure.persistence.orm.collaboration import (
    TaskCommentORM,
    TaskPresenceORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.modules.project_management.infrastructure.persistence.orm.task import TaskORM


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _list(value: str | None, *, lowercase: bool = False) -> tuple[str, ...]:
    try:
        decoded = json.loads(value or "[]")
    except (TypeError, ValueError):
        return ()
    if not isinstance(decoded, list):
        return ()
    items = tuple(str(item).strip() for item in decoded if str(item).strip())
    return tuple(item.lower() for item in items) if lowercase else items


class SqlAlchemyCollaborationWorkspaceReader:
    """Read cross-project Collaboration facts without owning authorization policy."""

    def __init__(self, *, session: Session) -> None:
        self._session = session

    def read_facts(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        accessible_project_ids: tuple[str, ...],
        comment_limit: int,
        presence_since: datetime | None = None,
        presence_limit: int = 0,
    ) -> CollaborationWorkspaceFacts:
        project_ids = tuple(dict.fromkeys(accessible_project_ids))
        if not project_ids:
            return CollaborationWorkspaceFacts(tenant_id, organization_id, (), ())
        project_scope = (
            ProjectORM.tenant_id == tenant_id,
            ProjectORM.organization_id == organization_id,
            ProjectORM.id.in_(project_ids),
        )
        comments = self._session.execute(
            select(TaskCommentORM, TaskORM.name, TaskORM.project_id, ProjectORM.name)
            .join(TaskORM, TaskORM.id == TaskCommentORM.task_id)
            .join(ProjectORM, ProjectORM.id == TaskORM.project_id)
            .where(*project_scope)
            .order_by(TaskCommentORM.created_at.desc())
            .limit(max(0, int(comment_limit)))
        ).all() if comment_limit > 0 else ()
        presence = ()
        if presence_since is not None and presence_limit > 0:
            presence = self._session.execute(
                select(TaskPresenceORM, TaskORM.name, TaskORM.project_id, ProjectORM.name)
                .join(TaskORM, TaskORM.id == TaskPresenceORM.task_id)
                .join(ProjectORM, ProjectORM.id == TaskORM.project_id)
                .where(*project_scope, TaskPresenceORM.last_seen_at >= presence_since)
                .order_by(TaskPresenceORM.last_seen_at.desc())
                .limit(max(0, int(presence_limit)))
            ).all()
        return CollaborationWorkspaceFacts(
            tenant_id=tenant_id,
            organization_id=organization_id,
            comments=tuple(
                CollaborationCommentFact(
                    comment_id=str(row.id),
                    task_id=str(row.task_id),
                    task_name=str(task_name or ""),
                    project_id=str(project_id),
                    project_name=str(project_name or ""),
                    author_user_id=(None if row.author_user_id is None else str(row.author_user_id)),
                    author_username=row.author_username,
                    body=str(row.body or ""),
                    mentions=_list(row.mentions_json, lowercase=True),
                    mentioned_user_ids=_list(row.mentioned_user_ids_json),
                    read_by=_list(row.read_by_json, lowercase=True),
                    read_by_user_ids=_list(row.read_by_user_ids_json),
                    created_at=_utc(row.created_at),
                )
                for row, task_name, project_id, project_name in comments
            ),
            active_presence=tuple(
                CollaborationPresenceFact(
                    task_id=str(row.task_id),
                    task_name=str(task_name or ""),
                    project_id=str(project_id),
                    project_name=str(project_name or ""),
                    user_id=(None if row.user_id is None else str(row.user_id)),
                    username=str(row.username or ""),
                    display_name=row.display_name,
                    activity=str(row.activity or "reviewing"),
                    last_seen_at=_utc(row.last_seen_at),
                )
                for row, task_name, project_id, project_name in presence
            ),
        )


__all__ = ["SqlAlchemyCollaborationWorkspaceReader"]
