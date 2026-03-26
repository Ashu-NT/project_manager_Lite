from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.platform.common.interfaces import ProjectMembershipRepository, ScopedAccessGrantRepository
from core.platform.common.models import ProjectMembership, ScopedAccessGrant
from infra.platform.db.access.mapper import (
    project_membership_from_orm,
    project_membership_to_orm,
    scoped_access_grant_from_orm,
    scoped_access_grant_to_orm,
)
from infra.platform.db.models import ProjectMembershipORM


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


class SqlAlchemyScopedAccessGrantRepository(ScopedAccessGrantRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, grant: ScopedAccessGrant) -> None:
        self.session.add(scoped_access_grant_to_orm(grant))

    def update(self, grant: ScopedAccessGrant) -> None:
        self.session.merge(scoped_access_grant_to_orm(grant))

    def get(self, grant_id: str) -> Optional[ScopedAccessGrant]:
        obj = self.session.get(ProjectMembershipORM, grant_id)
        return scoped_access_grant_from_orm(obj) if obj else None

    def get_for_scope_user(
        self,
        scope_type: str,
        scope_id: str,
        user_id: str,
    ) -> Optional[ScopedAccessGrant]:
        self._ensure_supported_scope_type(scope_type)
        stmt = select(ProjectMembershipORM).where(
            ProjectMembershipORM.project_id == scope_id,
            ProjectMembershipORM.user_id == user_id,
        )
        obj = self.session.execute(stmt).scalars().first()
        return scoped_access_grant_from_orm(obj) if obj else None

    def list_by_scope(self, scope_type: str, scope_id: str) -> List[ScopedAccessGrant]:
        self._ensure_supported_scope_type(scope_type)
        stmt = select(ProjectMembershipORM).where(ProjectMembershipORM.project_id == scope_id)
        rows = self.session.execute(stmt).scalars().all()
        return [scoped_access_grant_from_orm(row) for row in rows]

    def list_by_user(
        self,
        user_id: str,
        *,
        scope_type: str | None = None,
    ) -> List[ScopedAccessGrant]:
        if scope_type is not None:
            self._ensure_supported_scope_type(scope_type)
        stmt = select(ProjectMembershipORM).where(ProjectMembershipORM.user_id == user_id)
        rows = self.session.execute(stmt).scalars().all()
        return [scoped_access_grant_from_orm(row) for row in rows]

    def delete(self, grant_id: str) -> None:
        obj = self.session.get(ProjectMembershipORM, grant_id)
        if obj is not None:
            self.session.delete(obj)

    @staticmethod
    def _ensure_supported_scope_type(scope_type: str) -> None:
        normalized = str(scope_type or "").strip().lower()
        if normalized != "project":
            raise ValueError(f"Unsupported scope type: {scope_type}")


__all__ = ["SqlAlchemyProjectMembershipRepository", "SqlAlchemyScopedAccessGrantRepository"]
