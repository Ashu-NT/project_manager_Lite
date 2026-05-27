from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from src.core.modules.project_management.domain.resources.resource import Resource


class ResourceRepository(ABC):
    @abstractmethod
    def add(self, resource: Resource) -> None: ...

    @abstractmethod
    def update(self, resource: Resource) -> None: ...

    @abstractmethod
    def delete(self, resource_id: str) -> None: ...

    @abstractmethod
    def get(self, resource_id: str) -> Optional[Resource]: ...

    @abstractmethod
    def list_all(self) -> List[Resource]: ...

    @abstractmethod
    def list_by_employee(self, employee_id: str) -> List[Resource]: ...
