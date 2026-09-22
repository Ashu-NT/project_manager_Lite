from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.core.platform.infrastructure.persistence.mappers.master_data.employee.employee import (
    employee_from_orm,
    employee_to_orm,
)
from src.core.platform.infrastructure.persistence.orm.master_data.employee.employee import EmployeeORM
from src.core.platform.infrastructure.persistence.repositories._tenant_scope import (
    TenantScopedRepositorySupport,
)
from src.core.platform.contract.repositories.master_data.employee.contracts import EmployeeRepository
from src.core.platform.domain.master_data.employee import Employee
from src.infra.persistence.db.optimistic import update_with_version_check


class SqlAlchemyEmployeeRepository(TenantScopedRepositorySupport, EmployeeRepository):
    _repository_label = "EmployeeRepository"
    session: Session

    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service = None

    def add(self, employee: Employee) -> None:
        ctx = self._context(operation_label="access employees")
        orm = employee_to_orm(employee)
        orm.tenant_id = ctx.tenant_id
        orm.organization_id = ctx.organization_id
        self.session.add(orm)

    def update(self, employee: Employee) -> None:
        ctx = self._context(operation_label="access employees")
        employee.version = update_with_version_check(
            self.session,
            EmployeeORM,
            employee.id,
            getattr(employee, "version", 1),
            {
                "organization_id": ctx.organization_id,
                "employee_code": employee.employee_code,
                "full_name": employee.full_name,
                "department_id": employee.department_id,
                "department": (employee.department or None),
                "site_id": employee.site_id,
                "site_name": (employee.site_name or None),
                "title": (employee.title or None),
                "employment_type": employee.employment_type,
                "email": employee.email,
                "phone": employee.phone,
                "is_active": employee.is_active,
                "user_id": employee.user_id,
            },
            extra_filters={
                "tenant_id": ctx.tenant_id,
                "organization_id": ctx.organization_id,
            },
            not_found_message="Employee not found.",
            stale_message="Employee was updated by another user.",
        )

    def get(self, employee_id: str) -> Employee | None:
        ctx = self._context(operation_label="access employees")
        stmt = select(EmployeeORM).where(
            EmployeeORM.id == employee_id,
            EmployeeORM.tenant_id == ctx.tenant_id,
            EmployeeORM.organization_id == ctx.organization_id,
        )
        obj = self.session.execute(stmt).scalar_one_or_none()
        return employee_from_orm(obj) if obj else None

    def get_by_code(self, employee_code: str) -> Employee | None:
        ctx = self._context(operation_label="access employees")
        stmt = select(EmployeeORM).where(
            EmployeeORM.employee_code == employee_code,
            EmployeeORM.tenant_id == ctx.tenant_id,
            EmployeeORM.organization_id == ctx.organization_id,
        )
        obj = self.session.execute(stmt).scalars().first()
        return employee_from_orm(obj) if obj else None

    def get_for_organization(self, employee_id: str, organization_id: str) -> Employee | None:
        ctx = self._context(operation_label="access employees")
        if not self._organization_in_scope(ctx, organization_id):
            return None
        stmt = select(EmployeeORM).where(
            EmployeeORM.id == employee_id,
            EmployeeORM.organization_id == ctx.organization_id,
            EmployeeORM.tenant_id == ctx.tenant_id,
        )
        obj = self.session.execute(stmt).scalars().first()
        return employee_from_orm(obj) if obj else None

    def get_by_code_for_organization(self, employee_code: str, organization_id: str) -> Employee | None:
        ctx = self._context(operation_label="access employees")
        if not self._organization_in_scope(ctx, organization_id):
            return None
        stmt = select(EmployeeORM).where(
            EmployeeORM.employee_code == employee_code,
            EmployeeORM.organization_id == ctx.organization_id,
            EmployeeORM.tenant_id == ctx.tenant_id,
        )
        obj = self.session.execute(stmt).scalars().first()
        return employee_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        department_id: str | None = None,
        site_id: str | None = None,
    ) -> list[Employee]:
        ctx = self._context(operation_label="access employees")
        if not self._organization_in_scope(ctx, organization_id):
            return []
        stmt = select(EmployeeORM).where(
            EmployeeORM.organization_id == ctx.organization_id,
            EmployeeORM.tenant_id == ctx.tenant_id,
        )
        if active_only is not None:
            stmt = stmt.where(EmployeeORM.is_active == bool(active_only))
        if department_id is not None:
            stmt = stmt.where(EmployeeORM.department_id == department_id)
        if site_id is not None:
            stmt = stmt.where(EmployeeORM.site_id == site_id)
        rows = self.session.execute(stmt.order_by(EmployeeORM.full_name.asc())).scalars().all()
        return [employee_from_orm(row) for row in rows]

    def list_page_for_organization_in_tenant(
        self,
        organization_id: str,
        tenant_id: str,
        *,
        page: int,
        page_size: int,
        search: str | None = None,
        active_only: bool | None = None,
        department_id: str | None = None,
        site_id: str | None = None,
    ) -> tuple[list[Employee], int, int]:
        # Deliberately bypasses self._context()/_organization_in_scope() --
        # both organization_id and tenant_id are caller-supplied and trusted
        # (the service layer verifies the organization actually belongs to
        # this tenant before calling here), not the session's ambient active
        # organization. See SqlAlchemySiteRepository.list_page_for_organization_in_tenant
        # for the same pattern.
        base_condition = (
            EmployeeORM.organization_id == organization_id,
            EmployeeORM.tenant_id == tenant_id,
        )
        total = self.session.execute(
            select(func.count()).select_from(EmployeeORM).where(*base_condition)
        ).scalar_one()

        filtered_stmt = select(EmployeeORM).where(*base_condition)
        filtered_count_stmt = select(func.count()).select_from(EmployeeORM).where(*base_condition)
        if active_only is not None:
            condition = EmployeeORM.is_active == bool(active_only)
            filtered_stmt = filtered_stmt.where(condition)
            filtered_count_stmt = filtered_count_stmt.where(condition)
        if department_id is not None:
            condition = EmployeeORM.department_id == department_id
            filtered_stmt = filtered_stmt.where(condition)
            filtered_count_stmt = filtered_count_stmt.where(condition)
        if site_id is not None:
            condition = EmployeeORM.site_id == site_id
            filtered_stmt = filtered_stmt.where(condition)
            filtered_count_stmt = filtered_count_stmt.where(condition)
        normalized_search = (search or "").strip()
        if normalized_search:
            pattern = f"%{normalized_search}%"
            condition = or_(
                EmployeeORM.full_name.ilike(pattern),
                EmployeeORM.employee_code.ilike(pattern),
                EmployeeORM.title.ilike(pattern),
                EmployeeORM.email.ilike(pattern),
            )
            filtered_stmt = filtered_stmt.where(condition)
            filtered_count_stmt = filtered_count_stmt.where(condition)

        filtered_total = self.session.execute(filtered_count_stmt).scalar_one()
        offset = max(0, (page - 1) * page_size)
        rows = self.session.execute(
            filtered_stmt.order_by(EmployeeORM.full_name.asc()).offset(offset).limit(page_size)
        ).scalars().all()
        return [employee_from_orm(row) for row in rows], total, filtered_total


__all__ = [
    "SqlAlchemyEmployeeRepository",
]
