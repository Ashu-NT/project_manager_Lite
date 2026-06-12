from __future__ import annotations

import logging
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.modules.project_management.infrastructure.persistence.orm.project import (
    ProjectORM,
)
from src.core.platform.access.contracts import (
    ProjectMembershipRepository,
    ScopedAccessGrantRepository,
)
from src.core.platform.access.domain import ProjectMembership, ScopedAccessGrant
from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.infrastructure.persistence.mappers.access import (
    project_membership_from_orm,
    project_membership_to_orm,
    scoped_access_grant_from_orm,
    scoped_access_grant_to_orm,
)
from src.core.platform.infrastructure.persistence.orm.access import (
    ProjectMembershipORM,
    ScopedAccessGrantORM,
)

logger = logging.getLogger(__name__)

ScopedAccessRow = ProjectMembershipORM | ScopedAccessGrantORM


def _scoped_access_grants_from_rows(
    rows: Iterable[ScopedAccessRow | None],
    *,
    source: str,
) -> list[ScopedAccessGrant]:
    grants: list[ScopedAccessGrant] = []
    skipped_count = 0
    for row in rows:
        if row is None:
            skipped_count += 1
            continue
        grants.append(scoped_access_grant_from_orm(row))
    if skipped_count:
        logger.warning(
            "Skipped null scoped access rows source=%s skipped_count=%s",
            source,
            skipped_count,
        )
    return grants


class _AccessRepositoryScopeSupport:
    session: Session
    _tenant_context_service = None

    def _active_tenant_id(self) -> str | None:
        if self._tenant_context_service is None:
            return None
        user_session = getattr(self._tenant_context_service, "_user_session", None)
        if user_session is not None:
            tenant_id = str(getattr(user_session, "_active_tenant_id", "") or "").strip()
            if tenant_id:
                return tenant_id
        return self._tenant_context_service.get_active_tenant_id()

    def _active_organization_id(self) -> str | None:
        if self._tenant_context_service is None:
            return None
        user_session = getattr(self._tenant_context_service, "_user_session", None)
        if user_session is None:
            return None
        organization_id = str(
            getattr(user_session, "_active_organization_id", "") or ""
        ).strip()
        return organization_id or None

    def _scoped_project_membership_stmt(self, base_stmt):
        stmt = base_stmt.select_from(ProjectMembershipORM).join(
            ProjectORM,
            ProjectMembershipORM.project_id == ProjectORM.id,
        )
        tenant_id = self._active_tenant_id()
        if tenant_id is not None:
            stmt = stmt.where(ProjectORM.tenant_id == tenant_id)
        organization_id = self._active_organization_id()
        if organization_id is not None:
            stmt = stmt.where(ProjectORM.organization_id == organization_id)
        return stmt

    def _scoped_generic_grant_stmt(self, base_stmt):
        tenant_id = self._active_tenant_id()
        if tenant_id is None:
            return base_stmt
        return base_stmt.where(ScopedAccessGrantORM.tenant_id == tenant_id)

    def _require_project_in_scope(self, project_id: str) -> ProjectORM:
        stmt = select(ProjectORM).where(ProjectORM.id == project_id)
        tenant_id = self._active_tenant_id()
        if tenant_id is not None:
            stmt = stmt.where(ProjectORM.tenant_id == tenant_id)
        organization_id = self._active_organization_id()
        if organization_id is not None:
            stmt = stmt.where(ProjectORM.organization_id == organization_id)
        project = self.session.execute(stmt).scalar_one_or_none()
        if project is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        return project

    def _upsert_project_membership(self, membership: ProjectMembership) -> None:
        project = self._require_project_in_scope(membership.project_id)
        orm = project_membership_to_orm(membership)
        existing = self.session.execute(
            self._scoped_project_membership_stmt(select(ProjectMembershipORM)).where(
                ProjectMembershipORM.id == membership.id
            )
        ).scalar_one_or_none()
        if existing is None:
            orm.organization_id = project.organization_id
            self.session.add(orm)
            return
        existing.project_id = orm.project_id
        existing.user_id = orm.user_id
        existing.organization_id = project.organization_id
        existing.scope_role = orm.scope_role
        existing.permission_codes_json = orm.permission_codes_json
        existing.created_at = orm.created_at


class SqlAlchemyProjectMembershipRepository(
    _AccessRepositoryScopeSupport, ProjectMembershipRepository
):
    session: Session

    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service = None

    def add(self, membership: ProjectMembership) -> None:
        self._upsert_project_membership(membership)

    def update(self, membership: ProjectMembership) -> None:
        self._upsert_project_membership(membership)

    def get(self, membership_id: str) -> ProjectMembership | None:
        obj = self.session.execute(
            self._scoped_project_membership_stmt(select(ProjectMembershipORM)).where(
                ProjectMembershipORM.id == membership_id
            )
        ).scalar_one_or_none()
        return project_membership_from_orm(obj) if obj else None

    def get_for_project_user(
        self,
        project_id: str,
        user_id: str,
    ) -> ProjectMembership | None:
        stmt = self._scoped_project_membership_stmt(select(ProjectMembershipORM)).where(
            ProjectMembershipORM.project_id == project_id,
            ProjectMembershipORM.user_id == user_id,
        )
        obj = self.session.execute(stmt).scalars().first()
        return project_membership_from_orm(obj) if obj else None

    def list_by_project(self, project_id: str) -> list[ProjectMembership]:
        stmt = self._scoped_project_membership_stmt(select(ProjectMembershipORM)).where(
            ProjectMembershipORM.project_id == project_id
        )
        rows = self.session.execute(stmt).scalars().all()
        return [project_membership_from_orm(row) for row in rows]

    def list_by_user(self, user_id: str) -> list[ProjectMembership]:
        stmt = self._scoped_project_membership_stmt(select(ProjectMembershipORM)).where(
            ProjectMembershipORM.user_id == user_id
        )
        rows = self.session.execute(stmt).scalars().all()
        return [project_membership_from_orm(row) for row in rows]

    def delete(self, membership_id: str) -> None:
        obj = self.session.execute(
            self._scoped_project_membership_stmt(select(ProjectMembershipORM)).where(
                ProjectMembershipORM.id == membership_id
            )
        ).scalar_one_or_none()
        if obj is not None:
            self.session.delete(obj)


class SqlAlchemyScopedAccessGrantRepository(
    _AccessRepositoryScopeSupport, ScopedAccessGrantRepository
):
    session: Session

    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service = None

    def add(self, grant: ScopedAccessGrant) -> None:
        normalized_scope_type = self._normalize_scope_type(grant.scope_type)
        if normalized_scope_type == "project":
            self._upsert_project_membership(
                ProjectMembership.from_scoped_access_grant(grant)
            )
            return
        orm = scoped_access_grant_to_orm(grant)
        orm.tenant_id = self._active_tenant_id()
        self.session.add(orm)

    def update(self, grant: ScopedAccessGrant) -> None:
        normalized_scope_type = self._normalize_scope_type(grant.scope_type)
        if normalized_scope_type == "project":
            self._upsert_project_membership(
                ProjectMembership.from_scoped_access_grant(grant)
            )
            return
        orm = scoped_access_grant_to_orm(grant)
        existing = self.session.execute(
            self._scoped_generic_grant_stmt(select(ScopedAccessGrantORM)).where(
                ScopedAccessGrantORM.id == grant.id
            )
        ).scalar_one_or_none()
        if existing is None:
            orm.tenant_id = self._active_tenant_id()
            self.session.add(orm)
            return
        existing.tenant_id = self._active_tenant_id()
        existing.scope_type = orm.scope_type
        existing.scope_id = orm.scope_id
        existing.user_id = orm.user_id
        existing.scope_role = orm.scope_role
        existing.permission_codes_json = orm.permission_codes_json
        existing.created_at = orm.created_at

    def get(self, grant_id: str) -> ScopedAccessGrant | None:
        project_row = self.session.execute(
            self._scoped_project_membership_stmt(select(ProjectMembershipORM)).where(
                ProjectMembershipORM.id == grant_id
            )
        ).scalar_one_or_none()
        if project_row is not None:
            return scoped_access_grant_from_orm(project_row)
        generic_row = self.session.execute(
            self._scoped_generic_grant_stmt(select(ScopedAccessGrantORM)).where(
                ScopedAccessGrantORM.id == grant_id
            )
        ).scalar_one_or_none()
        return scoped_access_grant_from_orm(generic_row) if generic_row else None

    def get_for_scope_user(
        self,
        scope_type: str,
        scope_id: str,
        user_id: str,
    ) -> ScopedAccessGrant | None:
        normalized_scope_type = self._normalize_scope_type(scope_type)
        if normalized_scope_type == "project":
            stmt = self._scoped_project_membership_stmt(select(ProjectMembershipORM)).where(
                ProjectMembershipORM.project_id == scope_id,
                ProjectMembershipORM.user_id == user_id,
            )
            obj = self.session.execute(stmt).scalars().first()
            return scoped_access_grant_from_orm(obj) if obj else None
        stmt = self._scoped_generic_grant_stmt(select(ScopedAccessGrantORM)).where(
            ScopedAccessGrantORM.scope_type == normalized_scope_type,
            ScopedAccessGrantORM.scope_id == scope_id,
            ScopedAccessGrantORM.user_id == user_id,
        )
        obj = self.session.execute(stmt).scalars().first()
        return scoped_access_grant_from_orm(obj) if obj else None

    def list_by_scope(self, scope_type: str, scope_id: str) -> list[ScopedAccessGrant]:
        normalized_scope_type = self._normalize_scope_type(scope_type)
        if normalized_scope_type == "project":
            stmt = self._scoped_project_membership_stmt(select(ProjectMembershipORM)).where(
                ProjectMembershipORM.project_id == scope_id
            )
            rows = self.session.execute(stmt).scalars().all()
            return _scoped_access_grants_from_rows(rows, source="project_scope")
        stmt = self._scoped_generic_grant_stmt(select(ScopedAccessGrantORM)).where(
            ScopedAccessGrantORM.scope_type == normalized_scope_type,
            ScopedAccessGrantORM.scope_id == scope_id,
        )
        rows = self.session.execute(stmt).scalars().all()
        return _scoped_access_grants_from_rows(rows, source="generic_scope")

    def list_by_user(
        self,
        user_id: str,
        *,
        scope_type: str | None = None,
    ) -> list[ScopedAccessGrant]:
        normalized_scope_type = (
            self._normalize_scope_type(scope_type)
            if scope_type is not None
            else None
        )
        grants: list[ScopedAccessGrant] = []
        if normalized_scope_type in (None, "project"):
            stmt = self._scoped_project_membership_stmt(select(ProjectMembershipORM)).where(
                ProjectMembershipORM.user_id == user_id
            )
            rows = self.session.execute(stmt).scalars().all()
            grants.extend(_scoped_access_grants_from_rows(rows, source="project_user"))
        if normalized_scope_type != "project":
            stmt = self._scoped_generic_grant_stmt(select(ScopedAccessGrantORM)).where(
                ScopedAccessGrantORM.user_id == user_id
            )
            if normalized_scope_type is not None:
                stmt = stmt.where(ScopedAccessGrantORM.scope_type == normalized_scope_type)
            rows = self.session.execute(stmt).scalars().all()
            grants.extend(_scoped_access_grants_from_rows(rows, source="generic_user"))
        return grants

    def delete(self, grant_id: str) -> None:
        project_row = self.session.execute(
            self._scoped_project_membership_stmt(select(ProjectMembershipORM)).where(
                ProjectMembershipORM.id == grant_id
            )
        ).scalar_one_or_none()
        if project_row is not None:
            self.session.delete(project_row)
            return
        generic_row = self.session.execute(
            self._scoped_generic_grant_stmt(select(ScopedAccessGrantORM)).where(
                ScopedAccessGrantORM.id == grant_id
            )
        ).scalar_one_or_none()
        if generic_row is not None:
            self.session.delete(generic_row)

    @staticmethod
    def _normalize_scope_type(scope_type: str | None) -> str:
        normalized = str(scope_type or "").strip().lower()
        if not normalized:
            raise ValueError("Scope type is required.")
        return normalized


__all__ = [
    "SqlAlchemyProjectMembershipRepository",
    "SqlAlchemyScopedAccessGrantRepository",
]
