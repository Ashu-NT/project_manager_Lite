from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from src.core.platform.org.domain import Department, Employee, Organization, Site


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
    def list_all(self, *, active_only: bool | None = None) -> list[Employee]: ...


class OrganizationRepository(ABC):
    @abstractmethod
    def add(self, organization: Organization) -> None: ...

    @abstractmethod
    def update(self, organization: Organization) -> None: ...

    @abstractmethod
    def get(self, organization_id: str) -> Organization | None: ...

    @abstractmethod
    def get_by_code(self, organization_code: str) -> Organization | None: ...

    @abstractmethod
    def get_active(self) -> Organization | None: ...

    @abstractmethod
    def list_all(self, *, active_only: bool | None = None) -> list[Organization]: ...


class SiteRepository(ABC):
    @abstractmethod
    def add(self, site: Site) -> None: ...

    @abstractmethod
    def update(self, site: Site) -> None: ...

    @abstractmethod
    def get(self, site_id: str) -> Site | None: ...

    @abstractmethod
    def get_by_code(self, organization_id: str, site_code: str) -> Site | None: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
    ) -> list[Site]: ...


class DepartmentRepository(ABC):
    @abstractmethod
    def add(self, department: Department) -> None: ...

    @abstractmethod
    def update(self, department: Department) -> None: ...

    @abstractmethod
    def get(self, department_id: str) -> Department | None: ...

    @abstractmethod
    def get_by_code(self, organization_id: str, department_code: str) -> Department | None: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
    ) -> list[Department]: ...


class LinkedEmployeeResource(Protocol):
    id: str
    name: str
    role: str
    contact: str
    worker_type: object | None
    employee_id: str | None


class LinkedEmployeeResourceRepository(Protocol):
    def list_by_employee(self, employee_id: str) -> list[LinkedEmployeeResource]: ...

    def update(self, resource: LinkedEmployeeResource) -> None: ...


class LocationReference(Protocol):
    id: str
    organization_id: str
    site_id: str
    location_code: str
    name: str
    is_active: bool


class LocationReferenceRepository(Protocol):
    def get(self, location_id: str) -> LocationReference | None: ...

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
    ) -> list[LocationReference]: ...


__all__ = [
    "DepartmentRepository",
    "EmployeeRepository",
    "LinkedEmployeeResource",
    "LinkedEmployeeResourceRepository",
    "LocationReference",
    "LocationReferenceRepository",
    "OrganizationRepository",
    "SiteRepository",
]
