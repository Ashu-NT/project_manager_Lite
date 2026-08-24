"""Skill and certification query methods for ResourceService."""

from __future__ import annotations


from src.core.modules.project_management.contracts.repositories.resources.skills import (
    ResourceCertificationRepository,
    ResourceSkillRepository,
)
from src.core.modules.project_management.domain.resources.skills import (
    ResourceCertification,
    ResourceSkill,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)


class SkillQueryMixin:
    _skill_repo: ResourceSkillRepository | None
    _cert_repo: ResourceCertificationRepository | None

    def list_resource_skills(self, resource_id: str) -> list[ResourceSkill]:
        require_permission(
            self._user_session, "resource.read", operation_label="view resource skills"
        )
        if self._skill_repo is None:
            raise RuntimeError("Skill repository is not configured.")
        return self._skill_repo.list_by_resource(resource_id)

    def list_resource_certifications(self, resource_id: str) -> list[ResourceCertification]:
        require_permission(
            self._user_session,
            "resource.read",
            operation_label="view resource certifications",
        )
        if self._cert_repo is None:
            raise RuntimeError("Certification repository is not configured.")
        return self._cert_repo.list_by_resource(resource_id)


__all__ = ["SkillQueryMixin"]
