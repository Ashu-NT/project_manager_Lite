from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.modules.project_management.domain.resources.skills import (
    ResourceCertification,
    ResourceSkill,
    TaskSkillRequirement,
)


class ResourceSkillRepository(ABC):
    @abstractmethod
    def add(self, skill: ResourceSkill) -> ResourceSkill: ...

    @abstractmethod
    def get(self, skill_id: str) -> ResourceSkill | None: ...

    @abstractmethod
    def list_by_resource(self, resource_id: str) -> list[ResourceSkill]: ...

    @abstractmethod
    def count_by_resource(self, resource_id: str) -> int: ...

    @abstractmethod
    def update(self, skill: ResourceSkill, *, expected_version: int) -> ResourceSkill: ...

    @abstractmethod
    def code_exists(
        self, resource_id: str, skill_code: str, *, exclude_id: str | None = None
    ) -> bool: ...

    @abstractmethod
    def delete(self, skill_id: str, *, expected_version: int) -> None: ...


class ResourceCertificationRepository(ABC):
    @abstractmethod
    def add(self, cert: ResourceCertification) -> ResourceCertification: ...

    @abstractmethod
    def get(self, cert_id: str) -> ResourceCertification | None: ...

    @abstractmethod
    def list_by_resource(self, resource_id: str) -> list[ResourceCertification]: ...

    @abstractmethod
    def count_by_resource(self, resource_id: str) -> int: ...

    @abstractmethod
    def update(
        self, cert: ResourceCertification, *, expected_version: int
    ) -> ResourceCertification: ...

    @abstractmethod
    def code_exists(
        self, resource_id: str, certification_code: str, *, exclude_id: str | None = None
    ) -> bool: ...

    @abstractmethod
    def delete(self, cert_id: str, *, expected_version: int) -> None: ...


class TaskSkillRequirementRepository(ABC):
    @abstractmethod
    def add(self, req: TaskSkillRequirement) -> TaskSkillRequirement: ...

    @abstractmethod
    def get(self, req_id: str) -> TaskSkillRequirement | None: ...

    @abstractmethod
    def list_by_task(self, task_id: str) -> list[TaskSkillRequirement]: ...

    @abstractmethod
    def delete(self, req_id: str) -> None: ...


__all__ = [
    "ResourceSkillRepository",
    "ResourceCertificationRepository",
    "TaskSkillRequirementRepository",
]
