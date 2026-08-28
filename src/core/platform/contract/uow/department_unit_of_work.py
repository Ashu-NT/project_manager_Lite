from __future__ import annotations

from typing import Protocol

from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.contract.repositories.master_data.department.contracts import DepartmentRepository
from src.core.platform.contract.repositories.master_data.employee.contracts import EmployeeRepository
from src.core.platform.contract.repositories.master_data.site.contracts import SiteRepository
from src.core.shared.persistence.unit_of_work import UnitOfWork, UnitOfWorkFactory


class DepartmentUnitOfWork(UnitOfWork, Protocol):
    departments: DepartmentRepository
    sites: SiteRepository
    employees: EmployeeRepository
    _enterprise_audit_service: EnterpriseAuditService


class DepartmentUnitOfWorkFactory(UnitOfWorkFactory, Protocol):
    def create(self, *, context) -> DepartmentUnitOfWork: ...  # type: ignore[override]


__all__ = ["DepartmentUnitOfWork", "DepartmentUnitOfWorkFactory"]
