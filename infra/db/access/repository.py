from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.interfaces import ProjectMembershipRepository
from core.models import ProjectMembership
from infra.db.access.mapper import project_membership_from_orm, project_membership_to_orm
from infra.db.models import ProjectMembershipORM


class SqlAlchemyProjectMembershipRepository(ProjectMembershipRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, membership: ProjectMembership) -> None:
        self.session.add(project_membership_to_orm(membership))

    def update(self, membership: ProjectMembership) -> None:
        self.session.merge(project_membership_to_orm(membership))

    def get(self, membership_id: str) -> Optional[ProjectMembership]:
        obj = self.session.get(ProjectMembershipORM, membership_id)
        return project_membership_from_orm(obj) if obj else None

    def get_for_project_user(self, project_id: str, user_id: str) -> Optional[ProjectMembership]:
        stmt = select(ProjectMembershipORM).where(
            ProjectMembershipORM.project_id == project_id,
            ProjectMembershipORM.user_id == user_id,
        )
        obj = self.session.execute(stmt).scalars().first()
        return project_membership_from_orm(obj) if obj else None

    def list_by_project(self, project_id: str) -> List[ProjectMembership]:
        stmt = select(ProjectMembershipORM).where(ProjectMembershipORM.project_id == project_id)
        rows = self.session.execute(stmt).scalars().all()
        return [project_membership_from_orm(row) for row in rows]

    def list_by_user(self, user_id: str) -> List[ProjectMembership]:
        stmt = select(ProjectMembershipORM).where(ProjectMembershipORM.user_id == user_id)
        rows = self.session.execute(stmt).scalars().all()
        return [project_membership_from_orm(row) for row in rows]

    def delete(self, membership_id: str) -> None:
        obj = self.session.get(ProjectMembershipORM, membership_id)
        if obj is not None:
            self.session.delete(obj)


__all__ = ["SqlAlchemyProjectMembershipRepository"]
