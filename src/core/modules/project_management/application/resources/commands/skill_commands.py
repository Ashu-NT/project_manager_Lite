"""Skill and certification command methods for ResourceService."""

from __future__ import annotations

from datetime import date
from typing import Optional

from src.core.modules.project_management.contracts.repositories.skills import (
    ResourceCertificationRepository,
    ResourceSkillRepository,
)
from src.core.modules.project_management.domain.resources.skills import (
    ResourceCertification,
    ResourceSkill,
    SkillProficiencyLevel,
)
from src.core.platform.common.exceptions import NotFoundError


class SkillCommandMixin:
    _skill_repo: ResourceSkillRepository | None
    _cert_repo: ResourceCertificationRepository | None

    def add_resource_skill(
        self,
        resource_id: str,
        skill_code: str,
        skill_name: str,
        proficiency: str = "intermediate",
        notes: str = "",
    ) -> ResourceSkill:
        if self._skill_repo is None:
            raise RuntimeError("Skill repository is not configured.")
        try:
            prof = SkillProficiencyLevel(proficiency.lower())
        except ValueError:
            prof = SkillProficiencyLevel.INTERMEDIATE
        skill = ResourceSkill.create(
            resource_id=resource_id,
            skill_code=skill_code,
            skill_name=skill_name,
            proficiency=prof,
            notes=notes,
        )
        return self._skill_repo.add(skill)

    def remove_resource_skill(self, skill_id: str) -> None:
        if self._skill_repo is None:
            raise RuntimeError("Skill repository is not configured.")
        existing = self._skill_repo.get(skill_id)
        if existing is None:
            raise NotFoundError("Skill not found.", code="SKILL_NOT_FOUND")
        self._skill_repo.delete(skill_id)

    def add_resource_certification(
        self,
        resource_id: str,
        certification_code: str,
        certification_name: str,
        issued_date: Optional[date] = None,
        expiry_date: Optional[date] = None,
        issuing_body: str = "",
        notes: str = "",
    ) -> ResourceCertification:
        if self._cert_repo is None:
            raise RuntimeError("Certification repository is not configured.")
        cert = ResourceCertification.create(
            resource_id=resource_id,
            certification_code=certification_code,
            certification_name=certification_name,
            issued_date=issued_date,
            expiry_date=expiry_date,
            issuing_body=issuing_body,
            notes=notes,
        )
        return self._cert_repo.add(cert)

    def remove_resource_certification(self, cert_id: str) -> None:
        if self._cert_repo is None:
            raise RuntimeError("Certification repository is not configured.")
        existing = self._cert_repo.get(cert_id)
        if existing is None:
            raise NotFoundError("Certification not found.", code="CERT_NOT_FOUND")
        self._cert_repo.delete(cert_id)


__all__ = ["SkillCommandMixin"]
