from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.modules.project_management.domain.projects.project import Project, ProjectResource


class ProjectRepository(ABC):
    @abstractmethod
    def add(self, project: Project) -> None: ...

    @abstractmethod
    def update(self, project: Project) -> None: ...

    @abstractmethod
    def delete(self, project_id: str) -> None: ...

    @abstractmethod
    def get(self, project_id: str) -> Project | None: ...

    @abstractmethod
    def list(self) -> list[Project]: ...


class ProjectResourceRepository(ABC):
    @abstractmethod
    def add(self, pr: ProjectResource) -> None: ...

    @abstractmethod
    def get(self, pr_id: str) -> ProjectResource | None: ...

    @abstractmethod
    def list_by_project(self, project_id: str) -> list[ProjectResource]: ...

    @abstractmethod
    def get_for_project(self, project_id: str, resource_id: str) -> ProjectResource | None: ...

    @abstractmethod
    def delete(self, pr_id: str) -> None: ...

    @abstractmethod
    def delete_by_resource(self, res_id: str) -> None: ...

    @abstractmethod
    def update(self, pr: ProjectResource) -> None: ...

    @abstractmethod
    def update_with_version_check(
        self, pr: ProjectResource, *, expected_version: int
    ) -> ProjectResource:
        """Versioned write path for planning-mutable fields (hourly_rate,
        currency_code, planned_hours, is_active). Rejects with a
        ``ConcurrencyError`` if ``expected_version`` no longer matches the
        persisted row."""
        ...

    @abstractmethod
    def touch_version_with_check(self, pr_id: str, *, expected_version: int) -> int:
        """Advances only ``version`` (no other field changes) and returns
        the new value. Used by the assignment-level planned-hours
        reconciliation flow to make a concurrent envelope shrink and a
        concurrent allocation increase detectable against each other, even
        though neither operation, by itself, mutates the other's data."""
        ...
