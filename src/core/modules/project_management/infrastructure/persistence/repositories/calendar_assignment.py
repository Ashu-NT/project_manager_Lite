"""SQLAlchemy repositories for PM calendar assignment domain."""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.modules.project_management.domain.calendar.assignment import (
    ProjectCalendarAssignment,
    ResourceCalendarAssignment,
)
from src.core.modules.project_management.infrastructure.persistence.orm.calendar_assignment import (
    ProjectCalendarAssignmentORM,
    ResourceCalendarAssignmentORM,
)


def _project_from_orm(obj: ProjectCalendarAssignmentORM) -> ProjectCalendarAssignment:
    return ProjectCalendarAssignment(
        id=obj.id,
        project_id=obj.project_id,
        calendar_id=obj.calendar_id,
        effective_from=obj.effective_from,
        effective_to=obj.effective_to,
        is_default=obj.is_default,
        priority=obj.priority,
    )


def _resource_from_orm(obj: ResourceCalendarAssignmentORM) -> ResourceCalendarAssignment:
    return ResourceCalendarAssignment(
        id=obj.id,
        resource_id=obj.resource_id,
        calendar_id=obj.calendar_id,
        effective_from=obj.effective_from,
        effective_to=obj.effective_to,
        is_default=obj.is_default,
        priority=obj.priority,
    )


def _is_effective(effective_from, effective_to, at_date: Optional[date]) -> bool:
    if at_date is None:
        return True
    if effective_from is not None and at_date < effective_from:
        return False
    if effective_to is not None and at_date > effective_to:
        return False
    return True


class SqlAlchemyProjectCalendarAssignmentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(
        self, project_id: str, *, at_date: Optional[date] = None
    ) -> Optional[ProjectCalendarAssignment]:
        stmt = select(ProjectCalendarAssignmentORM).where(
            ProjectCalendarAssignmentORM.project_id == project_id
        ).order_by(
            ProjectCalendarAssignmentORM.priority.desc(),
            ProjectCalendarAssignmentORM.is_default.desc(),
        )
        rows = self._session.execute(stmt).scalars().all()
        for row in rows:
            if _is_effective(row.effective_from, row.effective_to, at_date):
                return _project_from_orm(row)
        return None

    def list_for_project(self, project_id: str) -> list[ProjectCalendarAssignment]:
        stmt = select(ProjectCalendarAssignmentORM).where(
            ProjectCalendarAssignmentORM.project_id == project_id
        ).order_by(ProjectCalendarAssignmentORM.priority.desc())
        rows = self._session.execute(stmt).scalars().all()
        return [_project_from_orm(r) for r in rows]

    def list_for_calendar(self, calendar_id: str) -> list[ProjectCalendarAssignment]:
        stmt = select(ProjectCalendarAssignmentORM).where(
            ProjectCalendarAssignmentORM.calendar_id == calendar_id
        )
        rows = self._session.execute(stmt).scalars().all()
        return [_project_from_orm(r) for r in rows]

    def save(self, assignment: ProjectCalendarAssignment) -> None:
        existing = self._session.get(ProjectCalendarAssignmentORM, assignment.id)
        if existing:
            existing.calendar_id = assignment.calendar_id
            existing.effective_from = assignment.effective_from
            existing.effective_to = assignment.effective_to
            existing.is_default = assignment.is_default
            existing.priority = assignment.priority
        else:
            self._session.add(
                ProjectCalendarAssignmentORM(
                    id=assignment.id,
                    project_id=assignment.project_id,
                    calendar_id=assignment.calendar_id,
                    effective_from=assignment.effective_from,
                    effective_to=assignment.effective_to,
                    is_default=assignment.is_default,
                    priority=assignment.priority,
                )
            )

    def delete(self, assignment_id: str) -> None:
        self._session.query(ProjectCalendarAssignmentORM).filter_by(
            id=assignment_id
        ).delete()


class SqlAlchemyResourceCalendarAssignmentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(
        self, resource_id: str, *, at_date: Optional[date] = None
    ) -> Optional[ResourceCalendarAssignment]:
        stmt = select(ResourceCalendarAssignmentORM).where(
            ResourceCalendarAssignmentORM.resource_id == resource_id
        ).order_by(
            ResourceCalendarAssignmentORM.priority.desc(),
            ResourceCalendarAssignmentORM.is_default.desc(),
        )
        rows = self._session.execute(stmt).scalars().all()
        for row in rows:
            if _is_effective(row.effective_from, row.effective_to, at_date):
                return _resource_from_orm(row)
        return None

    def list_for_resource(self, resource_id: str) -> list[ResourceCalendarAssignment]:
        stmt = select(ResourceCalendarAssignmentORM).where(
            ResourceCalendarAssignmentORM.resource_id == resource_id
        ).order_by(ResourceCalendarAssignmentORM.priority.desc())
        rows = self._session.execute(stmt).scalars().all()
        return [_resource_from_orm(r) for r in rows]

    def list_for_calendar(self, calendar_id: str) -> list[ResourceCalendarAssignment]:
        stmt = select(ResourceCalendarAssignmentORM).where(
            ResourceCalendarAssignmentORM.calendar_id == calendar_id
        )
        rows = self._session.execute(stmt).scalars().all()
        return [_resource_from_orm(r) for r in rows]

    def save(self, assignment: ResourceCalendarAssignment) -> None:
        existing = self._session.get(ResourceCalendarAssignmentORM, assignment.id)
        if existing:
            existing.calendar_id = assignment.calendar_id
            existing.effective_from = assignment.effective_from
            existing.effective_to = assignment.effective_to
            existing.is_default = assignment.is_default
            existing.priority = assignment.priority
        else:
            self._session.add(
                ResourceCalendarAssignmentORM(
                    id=assignment.id,
                    resource_id=assignment.resource_id,
                    calendar_id=assignment.calendar_id,
                    effective_from=assignment.effective_from,
                    effective_to=assignment.effective_to,
                    is_default=assignment.is_default,
                    priority=assignment.priority,
                )
            )

    def delete(self, assignment_id: str) -> None:
        self._session.query(ResourceCalendarAssignmentORM).filter_by(
            id=assignment_id
        ).delete()


__all__ = [
    "SqlAlchemyProjectCalendarAssignmentRepository",
    "SqlAlchemyResourceCalendarAssignmentRepository",
]
