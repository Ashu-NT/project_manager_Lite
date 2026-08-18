from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.modules.project_management.domain.resources.resource import Resource


class ResourceRepository(ABC):
    @abstractmethod
    def add(self, resource: Resource) -> None: ...

    @abstractmethod
    def update(self, resource: Resource) -> None: ...

    @abstractmethod
    def delete(self, resource_id: str) -> None: ...

    @abstractmethod
    def get(self, resource_id: str) -> Resource | None: ...

    @abstractmethod
    def list(self) -> list[Resource]: ...

    @abstractmethod
    def list_by_ids(self, resource_ids: list[str]) -> list[Resource]:
        """Batch fetch by id -- callers needing a subset of resources
        (a name-lookup map, a labor-cost breakdown, a leveling pass) must
        use this instead of a per-id ``get()`` loop or a whole-tenant
        ``list()`` filtered client-side."""
        ...

    @abstractmethod
    def list_by_employee(self, employee_id: str) -> list[Resource]: ...
