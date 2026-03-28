from __future__ import annotations

from typing import Protocol


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


__all__ = ["LinkedEmployeeResource", "LinkedEmployeeResourceRepository"]
