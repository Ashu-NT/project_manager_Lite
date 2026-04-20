from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from src.core.modules.project_management.domain.scheduling.baseline import BaselineTask, ProjectBaseline


class BaselineRepository(ABC):
    @abstractmethod
    def add_baseline(self, b: ProjectBaseline) -> ProjectBaseline: ...

    @abstractmethod
    def get_baseline(self, baseline_id: str) -> Optional[ProjectBaseline]: ...

    @abstractmethod
    def get_latest_for_project(self, project_id: str) -> Optional[ProjectBaseline]: ...

    @abstractmethod
    def list_for_project(self, project_id: str) -> List[ProjectBaseline]: ...

    @abstractmethod
    def delete_baseline(self, baseline_id: str) -> None: ...

    @abstractmethod
    def add_baseline_tasks(self, tasks: List[BaselineTask]) -> None: ...

    @abstractmethod
    def list_tasks(self, baseline_id: str) -> List[BaselineTask]: ...

    @abstractmethod
    def delete_tasks(self, baseline_id: str) -> None: ...
