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

    def list_for_organization(self, organization_id: str) -> list[Project]:
        return self.list()


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
