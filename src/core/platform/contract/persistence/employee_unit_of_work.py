from __future__ import annotations

from typing import Protocol

from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.contract.repositories.master_data.department.contracts import (
    DepartmentRepository,
)
from src.core.platform.contract.repositories.master_data.employee.contracts import (
    EmployeeRepository,
    LinkedEmployeeResourceRepository,
)
from src.core.platform.contract.repositories.master_data.site.contracts import SiteRepository
from src.core.shared.persistence.unit_of_work import UnitOfWork, UnitOfWorkFactory


class EmployeeUnitOfWork(UnitOfWork, Protocol):
    employees: EmployeeRepository
    resources: LinkedEmployeeResourceRepository
    sites: SiteRepository
    departments: DepartmentRepository
    _enterprise_audit_service: EnterpriseAuditService


class EmployeeUnitOfWorkFactory(UnitOfWorkFactory, Protocol):
    def create(self, *, context) -> EmployeeUnitOfWork: ...  # type: ignore[override]


__all__ = ["EmployeeUnitOfWork", "EmployeeUnitOfWorkFactory"]
