from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.core.modules.project_management.domain.resources.resource import Resource


@dataclass(frozen=True, slots=True)
class ResourceReferenceSummary:
    project_resources: int = 0
    task_assignments: int = 0
    time_entries: int = 0
    skills: int = 0
    certifications: int = 0

    @property
    def has_operational_references(self) -> bool:
        return bool(self.project_resources or self.task_assignments or self.time_entries)

    @property
    def has_any_references(self) -> bool:
        return bool(
            self.has_operational_references or self.skills or self.certifications
        )


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

    @abstractmethod
    def code_exists(self, code: str, *, exclude_id: str | None = None) -> bool: ...

    @abstractmethod
    def employee_link_exists(
        self,
        employee_id: str,
        *,
        exclude_id: str | None = None,
    ) -> bool: ...

    @abstractmethod
    def reference_summary(self, resource_id: str) -> ResourceReferenceSummary: ...


__all__ = ["ResourceReferenceSummary", "ResourceRepository"]
