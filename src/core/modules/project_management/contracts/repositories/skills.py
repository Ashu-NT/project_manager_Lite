from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from src.core.modules.project_management.domain.resources.skills import (
    ResourceCertification,
    ResourceSkill,
    TaskSkillRequirement,
)


class ResourceSkillRepository(ABC):
    @abstractmethod
    def add(self, skill: ResourceSkill) -> ResourceSkill: ...

    @abstractmethod
    def get(self, skill_id: str) -> Optional[ResourceSkill]: ...

    @abstractmethod
    def list_by_resource(self, resource_id: str) -> List[ResourceSkill]: ...

    @abstractmethod
    def delete(self, skill_id: str) -> None: ...


class ResourceCertificationRepository(ABC):
    @abstractmethod
    def add(self, cert: ResourceCertification) -> ResourceCertification: ...

    @abstractmethod
    def get(self, cert_id: str) -> Optional[ResourceCertification]: ...

    @abstractmethod
    def list_by_resource(self, resource_id: str) -> List[ResourceCertification]: ...

    @abstractmethod
    def delete(self, cert_id: str) -> None: ...


class TaskSkillRequirementRepository(ABC):
    @abstractmethod
    def add(self, req: TaskSkillRequirement) -> TaskSkillRequirement: ...

    @abstractmethod
    def get(self, req_id: str) -> Optional[TaskSkillRequirement]: ...

    @abstractmethod
    def list_by_task(self, task_id: str) -> List[TaskSkillRequirement]: ...

    @abstractmethod
    def delete(self, req_id: str) -> None: ...


__all__ = [
    "ResourceSkillRepository",
    "ResourceCertificationRepository",
    "TaskSkillRequirementRepository",
]
