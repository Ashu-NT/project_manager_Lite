"""Skill and certification query methods for ResourceService."""

from __future__ import annotations


from src.core.modules.project_management.contracts.repositories.skills import (
    ResourceCertificationRepository,
    ResourceSkillRepository,
)
from src.core.modules.project_management.domain.resources.skills import (
    ResourceCertification,
    ResourceSkill,
)


class SkillQueryMixin:
    _skill_repo: ResourceSkillRepository | None
    _cert_repo: ResourceCertificationRepository | None

    def list_resource_skills(self, resource_id: str) -> list[ResourceSkill]:
        if self._skill_repo is None:
            return []
        return self._skill_repo.list_by_resource(resource_id)

    def list_resource_certifications(self, resource_id: str) -> list[ResourceCertification]:
        if self._cert_repo is None:
            return []
        return self._cert_repo.list_by_resource(resource_id)


__all__ = ["SkillQueryMixin"]
