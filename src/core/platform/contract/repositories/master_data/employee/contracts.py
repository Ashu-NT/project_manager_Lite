from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Protocol

from src.core.platform.contract.interface.master_data.employee.contracts import (
    LinkedEmployeeResource,
)
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
        department_id: str | None = None,
        site_id: str | None = None,
    ) -> list[Employee]: ...

    @abstractmethod
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
        """Tenant-scoped only -- NOT filtered to the ambient active
        organization. For an admin viewing ANY organization's employees
        (e.g. Organization Detail's Employees tab) regardless of which
        organization is currently active in the caller's session. Returns
        (page_items, total_count, filtered_total_count)."""
        ...


class LinkedEmployeeResourceRepository(Protocol):
    def list_by_employee(self, employee_id: str) -> Sequence[LinkedEmployeeResource]: ...

    def update(self, resource: LinkedEmployeeResource) -> None: ...


__all__ = [
    "EmployeeRepository",
    "LinkedEmployeeResourceRepository",
]
