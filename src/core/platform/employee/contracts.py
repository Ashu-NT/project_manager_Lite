from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from src.core.platform.employee.domain import Employee


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


__all__ = [
    "EmployeeRepository",
    "LinkedEmployeeResource",
    "LinkedEmployeeResourceRepository",
]
