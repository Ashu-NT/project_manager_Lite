from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from src.core.platform.contract.interface.master_data.employee.contracts import LinkedEmployeeResource
from src.core.platform.domain.master_data.employee import Employee


class EmployeeRepository(ABC):
    @abstractmethod
    def add(self, employee: Employee) -> None: ...

    @abstractmethod
    def update(self, employee: Employee) -> None: ...

    @abstractmethod
    def get(self, employee_id: str) -> Employee | None: ...

    @abstractmethod
    def get_by_code(self, employee_code: str) -> Employee | None: ...

    @abstractmethod
    def get_for_organization(self, employee_id: str, organization_id: str) -> Employee | None: ...

    @abstractmethod
    def get_by_code_for_organization(self, employee_code: str, organization_id: str) -> Employee | None: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
    ) -> list[Employee]: ...


class LinkedEmployeeResourceRepository(Protocol):
    def list_by_employee(self, employee_id: str) -> list[LinkedEmployeeResource]: ...

    def update(self, resource: LinkedEmployeeResource) -> None: ...


__all__ = [
    "EmployeeRepository",
    "LinkedEmployeeResourceRepository",
]
