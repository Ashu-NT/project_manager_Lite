from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.core.platform.infrastructure.persistence.mappers.master_data.department.departments import (
    department_from_orm,
    department_to_orm,
)
from src.core.platform.infrastructure.persistence.orm.master_data.department.departments import DepartmentORM
from src.core.platform.infrastructure.persistence.repositories._tenant_scope import (
    TenantScopedRepositorySupport,
)
from src.core.platform.contract.repositories.master_data.department.contracts import DepartmentRepository
from src.core.platform.domain.master_data.department import Department
from src.infra.persistence.db.optimistic import update_with_version_check


class SqlAlchemyDepartmentRepository(TenantScopedRepositorySupport, DepartmentRepository):
    _repository_label = "DepartmentRepository"
    session: Session

    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service = None

    def add(self, department: Department) -> None:
        ctx = self._context(operation_label="access departments")
        orm = department_to_orm(department)
        orm.tenant_id = ctx.tenant_id
        orm.organization_id = ctx.organization_id
        self.session.add(orm)

    def update(self, department: Department) -> None:
        ctx = self._context(operation_label="access departments")
        department.version = update_with_version_check(
            self.session,
            DepartmentORM,
            department.id,
            getattr(department, "version", 1),
            {
                "department_code": department.department_code,
                "name": department.name,
                "description": department.description or None,
                "site_id": department.site_id,
                "parent_department_id": department.parent_department_id,
                "department_type": department.department_type or None,
                "cost_center_code": department.cost_center_code or None,
                "manager_employee_id": department.manager_employee_id,
                "is_active": department.is_active,
                "created_at": department.created_at,
                "updated_at": department.updated_at,
                "notes": department.notes or None,
            },
            extra_filters={
                "tenant_id": ctx.tenant_id,
                "organization_id": ctx.organization_id,
            },
            not_found_message="Department not found.",
            stale_message="Department was updated by another user.",
        )

    def get(self, department_id: str) -> Department | None:
        ctx = self._context(operation_label="access departments")
        stmt = select(DepartmentORM).where(
            DepartmentORM.id == department_id,
            DepartmentORM.tenant_id == ctx.tenant_id,
            DepartmentORM.organization_id == ctx.organization_id,
        )
        obj = self.session.execute(stmt).scalar_one_or_none()
        return department_from_orm(obj) if obj else None

    def get_by_code(self, organization_id: str, department_code: str) -> Department | None:
        ctx = self._context(operation_label="access departments")
        if not self._organization_in_scope(ctx, organization_id):
            return None
        stmt = select(DepartmentORM).where(
            DepartmentORM.organization_id == ctx.organization_id,
            DepartmentORM.department_code == department_code,
            DepartmentORM.tenant_id == ctx.tenant_id,
        )
        obj = self.session.execute(stmt).scalars().first()
        return department_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
    ) -> list[Department]:
        ctx = self._context(operation_label="access departments")
        if not self._organization_in_scope(ctx, organization_id):
            return []
        stmt = select(DepartmentORM).where(
            DepartmentORM.organization_id == ctx.organization_id,
            DepartmentORM.tenant_id == ctx.tenant_id,
        )
        if active_only is not None:
            stmt = stmt.where(DepartmentORM.is_active == bool(active_only))
        if site_id is not None:
            stmt = stmt.where(DepartmentORM.site_id == site_id)
        rows = self.session.execute(stmt.order_by(DepartmentORM.name.asc())).scalars().all()
        return [department_from_orm(row) for row in rows]

    def list_page_for_organization_in_tenant(
        self,
        organization_id: str,
        tenant_id: str,
        *,
        page: int,
        page_size: int,
        search: str | None = None,
        active_only: bool | None = None,
        site_id: str | None = None,
    ) -> tuple[list[Department], int, int]:
        # Deliberately bypasses self._context()/_organization_in_scope() --
        # both organization_id and tenant_id are caller-supplied and trusted
        # (the service layer verifies the organization actually belongs to
        # this tenant before calling here), not the session's ambient active
        # organization. See SqlAlchemySiteRepository.list_page_for_organization_in_tenant
        # for the same pattern.
        base_condition = [
            DepartmentORM.organization_id == organization_id,
            DepartmentORM.tenant_id == tenant_id,
        ]
        if site_id is not None:
            base_condition.append(DepartmentORM.site_id == site_id)
        total = self.session.execute(
            select(func.count()).select_from(DepartmentORM).where(*base_condition)
        ).scalar_one()

        filtered_stmt = select(DepartmentORM).where(*base_condition)
        filtered_count_stmt = select(func.count()).select_from(DepartmentORM).where(*base_condition)
        if active_only is not None:
            condition = DepartmentORM.is_active == bool(active_only)
            filtered_stmt = filtered_stmt.where(condition)
            filtered_count_stmt = filtered_count_stmt.where(condition)
        normalized_search = (search or "").strip()
        if normalized_search:
            pattern = f"%{normalized_search}%"
            condition = or_(
                DepartmentORM.name.ilike(pattern),
                DepartmentORM.department_code.ilike(pattern),
                DepartmentORM.department_type.ilike(pattern),
                DepartmentORM.cost_center_code.ilike(pattern),
            )
            filtered_stmt = filtered_stmt.where(condition)
            filtered_count_stmt = filtered_count_stmt.where(condition)

        filtered_total = self.session.execute(filtered_count_stmt).scalar_one()
        offset = max(0, (page - 1) * page_size)
        rows = self.session.execute(
            filtered_stmt.order_by(DepartmentORM.name.asc()).offset(offset).limit(page_size)
        ).scalars().all()
        return [department_from_orm(row) for row in rows], total, filtered_total


__all__ = [
    "SqlAlchemyDepartmentRepository",
]
