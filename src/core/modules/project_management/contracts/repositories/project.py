from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from core.modules.project_management.domain.project import Project, ProjectResource


class ProjectRepository(ABC):
    @abstractmethod
    def add(self, project: Project) -> None: ...

    @abstractmethod
    def update(self, project: Project) -> None: ...

    @abstractmethod
    def delete(self, project_id: str) -> None: ...

    @abstractmethod
    def get(self, project_id: str) -> Optional[Project]: ...

    @abstractmethod
    def list_all(self) -> List[Project]: ...


class ProjectResourceRepository(ABC):
    @abstractmethod
    def add(self, pr: ProjectResource) -> None: ...

    @abstractmethod
    def get(self, pr_id: str) -> Optional[ProjectResource]: ...

    @abstractmethod
    def list_by_project(self, project_id: str) -> List[ProjectResource]: ...

    @abstractmethod
    def get_for_project(self, project_id: str, resource_id: str) -> Optional[ProjectResource]: ...

    @abstractmethod
    def delete(self, pr_id: str) -> None: ...

    @abstractmethod
    def delete_by_resource(self, res_id: str) -> None: ...

    @abstractmethod
    def update(self, pr: ProjectResource) -> None: ...
