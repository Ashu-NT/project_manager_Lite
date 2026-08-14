from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.reads.collaboration.models.workspace_facts import (
    CollaborationCommentFact,
    CollaborationCommentCriteria,
    CollaborationCommentReadPage,
    CollaborationPresenceFact,
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

    @staticmethod
    def _comment_fact(row, task_name, project_id, project_name) -> CollaborationCommentFact:
        return CollaborationCommentFact(
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

    def read_comment_authors(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        accessible_project_ids: tuple[str, ...],
    ) -> tuple[str, ...]:
        project_ids = tuple(dict.fromkeys(accessible_project_ids))
        if not project_ids:
            return ()
        rows = self._session.scalars(
            select(TaskCommentORM.author_username)
            .join(TaskORM, TaskORM.id == TaskCommentORM.task_id)
            .join(ProjectORM, ProjectORM.id == TaskORM.project_id)
            .where(
                ProjectORM.tenant_id == tenant_id,
                ProjectORM.organization_id == organization_id,
                ProjectORM.id.in_(project_ids),
                TaskCommentORM.author_username.is_not(None),
                TaskCommentORM.author_username != "",
            )
            .distinct()
            .order_by(TaskCommentORM.author_username.asc())
        ).all()
        return tuple(str(row).strip() for row in rows if str(row).strip())

    def read_comment_page(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        accessible_project_ids: tuple[str, ...],
        criteria: CollaborationCommentCriteria,
        page: int,
        page_size: int,
    ) -> CollaborationCommentReadPage:
        project_ids = tuple(dict.fromkeys(accessible_project_ids))
        if not project_ids:
            return CollaborationCommentReadPage(page=page, page_size=page_size)

        filters = [
            ProjectORM.tenant_id == tenant_id,
            ProjectORM.organization_id == organization_id,
            ProjectORM.id.in_(project_ids),
        ]
        if criteria.project_id:
            filters.append(ProjectORM.id == criteria.project_id)
        if criteria.author_username:
            filters.append(
                func.lower(func.coalesce(TaskCommentORM.author_username, ""))
                == criteria.author_username.lower()
            )
        if criteria.created_since is not None:
            filters.append(TaskCommentORM.created_at >= criteria.created_since)

        aliases = tuple(
            dict.fromkeys(
                str(alias or "").strip().lower()
                for alias in criteria.mention_aliases
                if str(alias or "").strip()
            )
        )
        mention_conditions = [
            func.lower(func.coalesce(TaskCommentORM.mentions_json, "")).contains(
                json.dumps(alias)
            )
            for alias in aliases
        ]
        if criteria.principal_user_id:
            mention_conditions.append(
                func.coalesce(TaskCommentORM.mentioned_user_ids_json, "").contains(
                    json.dumps(criteria.principal_user_id)
                )
            )
        if criteria.principal_mentions_only:
            if not mention_conditions:
                return CollaborationCommentReadPage(page=page, page_size=page_size)
            filters.append(or_(*mention_conditions))

        if criteria.unread_only:
            read_conditions = [
                func.lower(func.coalesce(TaskCommentORM.read_by_json, "")).contains(
                    json.dumps(alias)
                )
                for alias in aliases
            ]
            if criteria.principal_user_id:
                read_conditions.append(
                    func.coalesce(TaskCommentORM.read_by_user_ids_json, "").contains(
                        json.dumps(criteria.principal_user_id)
                    )
                )
            if read_conditions:
                filters.append(~or_(*read_conditions))

        if criteria.search_text:
            escaped = (
                criteria.search_text.replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            pattern = f"%{escaped.lower()}%"
            filters.append(
                or_(
                    func.lower(TaskCommentORM.body).like(pattern, escape="\\"),
                    func.lower(func.coalesce(TaskCommentORM.author_username, "")).like(
                        pattern, escape="\\"
                    ),
                    func.lower(TaskORM.name).like(pattern, escape="\\"),
                    func.lower(ProjectORM.name).like(pattern, escape="\\"),
                )
            )

        base = (
            select(TaskCommentORM, TaskORM.name, TaskORM.project_id, ProjectORM.name)
            .join(TaskORM, TaskORM.id == TaskCommentORM.task_id)
            .join(ProjectORM, ProjectORM.id == TaskORM.project_id)
            .where(*filters)
        )
        total = int(
            self._session.scalar(
                select(func.count()).select_from(base.with_only_columns(TaskCommentORM.id).subquery())
            )
            or 0
        )
        rows = self._session.execute(
            base.order_by(TaskCommentORM.created_at.desc(), TaskCommentORM.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return CollaborationCommentReadPage(
            items=tuple(self._comment_fact(*row) for row in rows),
            total=total,
            page=page,
            page_size=page_size,
        )

    def read_active_presence(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        accessible_project_ids: tuple[str, ...],
        active_since: datetime,
    ) -> tuple[CollaborationPresenceFact, ...]:
        project_ids = tuple(dict.fromkeys(accessible_project_ids))
        if not project_ids:
            return ()
        project_scope = (
            ProjectORM.tenant_id == tenant_id,
            ProjectORM.organization_id == organization_id,
            ProjectORM.id.in_(project_ids),
        )
        rows = self._session.execute(
            select(TaskPresenceORM, TaskORM.name, TaskORM.project_id, ProjectORM.name)
            .join(TaskORM, TaskORM.id == TaskPresenceORM.task_id)
            .join(ProjectORM, ProjectORM.id == TaskORM.project_id)
            .where(*project_scope, TaskPresenceORM.last_seen_at >= active_since)
            .order_by(TaskPresenceORM.last_seen_at.desc(), TaskPresenceORM.id.asc())
        ).all()
        return tuple(
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
            for row, task_name, project_id, project_name in rows
        )


__all__ = ["SqlAlchemyCollaborationWorkspaceReader"]
