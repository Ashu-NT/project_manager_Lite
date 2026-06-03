from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.platform.department.domain import Department


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


__all__ = ["DepartmentRepository"]
