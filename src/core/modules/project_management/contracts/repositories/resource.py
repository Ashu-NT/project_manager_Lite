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
    def get_for_organization(self, resource_id: str, organization_id: str) -> Resource | None: ...

    @abstractmethod
    def list_for_organization(self, organization_id: str) -> list[Resource]: ...

    @abstractmethod
    def list_by_employee(self, employee_id: str) -> list[Resource]: ...
