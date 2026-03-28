from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.platform.common.interfaces import ProjectMembershipRepository, ScopedAccessGrantRepository
from core.platform.access.domain import ProjectMembership, ScopedAccessGrant
from infra.platform.db.access.mapper import (
    project_membership_from_orm,
    project_membership_to_orm,
    scoped_access_grant_from_orm,
    scoped_access_grant_to_orm,
)
from infra.platform.db.models import ProjectMembershipORM, ScopedAccessGrantORM


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
        project_row = self.session.get(ProjectMembershipORM, grant_id)
        if project_row is not None:
            return scoped_access_grant_from_orm(project_row)
        generic_row = self.session.get(ScopedAccessGrantORM, grant_id)
        return scoped_access_grant_from_orm(generic_row) if generic_row else None

    def get_for_scope_user(
        self,
        scope_type: str,
        scope_id: str,
        user_id: str,
    ) -> Optional[ScopedAccessGrant]:
        normalized_scope_type = self._normalize_scope_type(scope_type)
        if normalized_scope_type == "project":
            stmt = select(ProjectMembershipORM).where(
                ProjectMembershipORM.project_id == scope_id,
                ProjectMembershipORM.user_id == user_id,
            )
            obj = self.session.execute(stmt).scalars().first()
            return scoped_access_grant_from_orm(obj) if obj else None
        stmt = select(ScopedAccessGrantORM).where(
            ScopedAccessGrantORM.scope_type == normalized_scope_type,
            ScopedAccessGrantORM.scope_id == scope_id,
            ScopedAccessGrantORM.user_id == user_id,
        )
        obj = self.session.execute(stmt).scalars().first()
        return scoped_access_grant_from_orm(obj) if obj else None

    def list_by_scope(self, scope_type: str, scope_id: str) -> List[ScopedAccessGrant]:
        normalized_scope_type = self._normalize_scope_type(scope_type)
        if normalized_scope_type == "project":
            stmt = select(ProjectMembershipORM).where(ProjectMembershipORM.project_id == scope_id)
            rows = self.session.execute(stmt).scalars().all()
            return [scoped_access_grant_from_orm(row) for row in rows]
        stmt = select(ScopedAccessGrantORM).where(
            ScopedAccessGrantORM.scope_type == normalized_scope_type,
            ScopedAccessGrantORM.scope_id == scope_id,
        )
        rows = self.session.execute(stmt).scalars().all()
        return [scoped_access_grant_from_orm(row) for row in rows]

    def list_by_user(
        self,
        user_id: str,
        *,
        scope_type: str | None = None,
    ) -> List[ScopedAccessGrant]:
        normalized_scope_type = (
            self._normalize_scope_type(scope_type)
            if scope_type is not None
            else None
        )
        grants: list[ScopedAccessGrant] = []
        if normalized_scope_type in (None, "project"):
            stmt = select(ProjectMembershipORM).where(ProjectMembershipORM.user_id == user_id)
            rows = self.session.execute(stmt).scalars().all()
            grants.extend(scoped_access_grant_from_orm(row) for row in rows)
        if normalized_scope_type != "project":
            stmt = select(ScopedAccessGrantORM).where(ScopedAccessGrantORM.user_id == user_id)
            if normalized_scope_type is not None:
                stmt = stmt.where(ScopedAccessGrantORM.scope_type == normalized_scope_type)
            rows = self.session.execute(stmt).scalars().all()
            grants.extend(scoped_access_grant_from_orm(row) for row in rows)
        return grants

    def delete(self, grant_id: str) -> None:
        project_row = self.session.get(ProjectMembershipORM, grant_id)
        if project_row is not None:
            self.session.delete(project_row)
            return
        generic_row = self.session.get(ScopedAccessGrantORM, grant_id)
        if generic_row is not None:
            self.session.delete(generic_row)

    @staticmethod
    def _normalize_scope_type(scope_type: str | None) -> str:
        normalized = str(scope_type or "").strip().lower()
        if not normalized:
            raise ValueError("Scope type is required.")
        return normalized


__all__ = ["SqlAlchemyProjectMembershipRepository", "SqlAlchemyScopedAccessGrantRepository"]
