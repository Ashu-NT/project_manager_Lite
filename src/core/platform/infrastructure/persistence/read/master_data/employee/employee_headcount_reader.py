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

from src.core.platform.contract.master_data.employee.read.employee_headcount_reader import (
    EmployeeHeadcountSummary,
)
from src.core.platform.infrastructure.persistence.orm.master_data.employee.employee import EmployeeORM


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


__all__ = ["SqlAlchemyEmployeeHeadcountReader"]
