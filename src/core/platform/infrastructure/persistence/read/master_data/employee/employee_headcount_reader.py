"""Concrete, tenant-scoped single-query read for employee headcount.

One dedicated read-side adapter -- not the write repository's
``list_for_organization`` fully hydrating every ``Employee`` row just to
compute two integers. ``EmployeeService`` depends on
``EmployeeHeadcountReader`` (``contract/master_data/employee/read/
employee_headcount_reader.py``), never on this concrete class directly.
Takes ``tenant_id``/``organization_id`` explicitly rather than resolving
them from ambient session state, matching the P1
``SqlAlchemyModuleEntitlementReader`` precedent.
"""

from __future__ import annotations

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from src.core.platform.contract.read.master_data.employee.employee_headcount_reader import (
    EmployeeDepartmentBreakdownRow,
    EmployeeHeadcountSummary,
    EmployeeSiteBreakdownRow,
)
from src.core.platform.infrastructure.persistence.orm.master_data.department.departments import DepartmentORM
from src.core.platform.infrastructure.persistence.orm.master_data.employee.employee import EmployeeORM
from src.core.platform.infrastructure.persistence.orm.master_data.site.sites import SiteORM


class SqlAlchemyEmployeeHeadcountReader:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_summary(self, *, tenant_id: str, organization_id: str) -> EmployeeHeadcountSummary:
        total, active = self._session.execute(
            select(
                func.count(EmployeeORM.id),
                func.sum(case((EmployeeORM.is_active.is_(True), 1), else_=0)),
            ).where(
                EmployeeORM.organization_id == organization_id,
                EmployeeORM.tenant_id == tenant_id,
            )
        ).one()
        return EmployeeHeadcountSummary(total=int(total or 0), active=int(active or 0))

    def get_department_breakdown(
        self, *, tenant_id: str, organization_id: str
    ) -> tuple[EmployeeDepartmentBreakdownRow, ...]:
        rows = self._session.execute(
            select(
                EmployeeORM.department_id,
                DepartmentORM.name,
                func.count(EmployeeORM.id),
                func.sum(case((EmployeeORM.is_active.is_(True), 1), else_=0)),
            )
            .select_from(EmployeeORM)
            .outerjoin(DepartmentORM, DepartmentORM.id == EmployeeORM.department_id)
            .where(
                EmployeeORM.organization_id == organization_id,
                EmployeeORM.tenant_id == tenant_id,
            )
            .group_by(EmployeeORM.department_id, DepartmentORM.name)
            .order_by(DepartmentORM.name.asc().nulls_last())
        ).all()
        return tuple(
            EmployeeDepartmentBreakdownRow(
                department_id=department_id,
                department_name=name or "Unassigned",
                total=int(total or 0),
                active=int(active or 0),
            )
            for department_id, name, total, active in rows
        )

    def get_site_breakdown(
        self, *, tenant_id: str, organization_id: str
    ) -> tuple[EmployeeSiteBreakdownRow, ...]:
        rows = self._session.execute(
            select(
                EmployeeORM.site_id,
                SiteORM.name,
                func.count(EmployeeORM.id),
                func.sum(case((EmployeeORM.is_active.is_(True), 1), else_=0)),
            )
            .select_from(EmployeeORM)
            .outerjoin(SiteORM, SiteORM.id == EmployeeORM.site_id)
            .where(
                EmployeeORM.organization_id == organization_id,
                EmployeeORM.tenant_id == tenant_id,
            )
            .group_by(EmployeeORM.site_id, SiteORM.name)
            .order_by(SiteORM.name.asc().nulls_last())
        ).all()
        return tuple(
            EmployeeSiteBreakdownRow(
                site_id=site_id,
                site_name=name or "Unassigned",
                total=int(total or 0),
                active=int(active or 0),
            )
            for site_id, name, total, active in rows
        )


__all__ = ["SqlAlchemyEmployeeHeadcountReader"]
