from __future__ import annotations

from abc import ABC, abstractmethod

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
    def find_by_user_id(self, user_id: str) -> Employee | None:
        """The one Employee (if any) already linked to this User account --
        enforces the optional one-to-one Employee<->User invariant at the
        application layer, on top of the DB's own partial unique index."""
        ...

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


__all__ = [
    "EmployeeRepository",
]
