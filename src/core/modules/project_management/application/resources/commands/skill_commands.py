"""Skill and certification command methods for ResourceService."""

from __future__ import annotations

from dataclasses import replace
from datetime import date

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
from src.core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from src.core.shared.activity import record_activity


class SkillCommandMixin:
    _skill_repo: ResourceSkillRepository | None
    _cert_repo: ResourceCertificationRepository | None

    def _stage_capability_activity(self, child, *, action: str) -> None:
        record_activity(
            self,
            action=action,
            entity_type="resource",
            entity_id=child.resource_id,
            module="project_management",
            details={
                "child_id": child.id,
                "child_version": child.version,
                "capability_type": type(child).__name__,
            },
            commit=False,
        )

    def add_resource_skill(
        self,
        resource_id: str,
        skill_code: str,
        skill_name: str,
        proficiency: str = "intermediate",
        notes: str = "",
    ) -> ResourceSkill:
        require_permission(
            self._user_session, "resource.manage", operation_label="add resource skill"
        )
        if self._skill_repo is None:
            raise RuntimeError("Skill repository is not configured.")
        skill = ResourceSkill.create(
            resource_id=resource_id,
            skill_code=skill_code,
            skill_name=skill_name,
            proficiency=proficiency,
            notes=notes,
        )
        if self._skill_repo.code_exists(resource_id, skill.skill_code):
            raise ValidationError(
                "This skill is already recorded for the resource.",
                code="RESOURCE_SKILL_DUPLICATE",
            )
        created = self._skill_repo.add(skill)
        self._stage_capability_activity(created, action="resource.skill.added")
        return created

    def update_resource_skill(
        self,
        *,
        skill_id: str,
        expected_version: int,
        skill_code: str,
        skill_name: str,
        proficiency: str = "intermediate",
        notes: str = "",
    ) -> ResourceSkill:
        require_permission(
            self._user_session, "resource.manage", operation_label="update resource skill"
        )
        if self._skill_repo is None:
            raise RuntimeError("Skill repository is not configured.")
        existing = self._skill_repo.get(skill_id)
        if existing is None:
            raise NotFoundError("Skill not found.", code="SKILL_NOT_FOUND")
        if existing.version != expected_version:
            raise ConcurrencyError(
                "Skill changed since you opened it.", code="STALE_WRITE"
            )
        candidate = replace(
            existing,
            skill_code=skill_code,
            skill_name=skill_name,
            proficiency=proficiency,
            notes=notes,
        )
        if self._skill_repo.code_exists(
            existing.resource_id, candidate.skill_code, exclude_id=existing.id
        ):
            raise ValidationError(
                "This skill is already recorded for the resource.",
                code="RESOURCE_SKILL_DUPLICATE",
            )
        updated = self._skill_repo.update(candidate, expected_version=expected_version)
        self._stage_capability_activity(updated, action="resource.skill.updated")
        return updated

    def remove_resource_skill(self, skill_id: str, *, expected_version: int) -> ResourceSkill:
        require_permission(
            self._user_session, "resource.manage", operation_label="remove resource skill"
        )
        if self._skill_repo is None:
            raise RuntimeError("Skill repository is not configured.")
        existing = self._skill_repo.get(skill_id)
        if existing is None:
            raise NotFoundError("Skill not found.", code="SKILL_NOT_FOUND")
        if existing.version != expected_version:
            raise ConcurrencyError(
                "Skill changed since you opened it.", code="STALE_WRITE"
            )
        self._stage_capability_activity(existing, action="resource.skill.removed")
        self._skill_repo.delete(skill_id, expected_version=expected_version)
        return existing

    def add_resource_certification(
        self,
        resource_id: str,
        certification_code: str,
        certification_name: str,
        issued_date: date | None = None,
        expiry_date: date | None = None,
        certificate_number: str = "",
        issuer: str = "",
        notes: str = "",
    ) -> ResourceCertification:
        require_permission(
            self._user_session,
            "resource.manage",
            operation_label="add resource certification",
        )
        if self._cert_repo is None:
            raise RuntimeError("Certification repository is not configured.")
        cert = ResourceCertification.create(
            resource_id=resource_id,
            certification_code=certification_code,
            certification_name=certification_name,
            issued_date=issued_date,
            expiry_date=expiry_date,
            certificate_number=certificate_number,
            issuer=issuer,
            notes=notes,
        )
        if self._cert_repo.code_exists(resource_id, cert.certification_code):
            raise ValidationError(
                "This certification is already recorded for the resource.",
                code="RESOURCE_CERTIFICATION_DUPLICATE",
            )
        created = self._cert_repo.add(cert)
        self._stage_capability_activity(created, action="resource.certification.added")
        return created

    def update_resource_certification(
        self,
        *,
        cert_id: str,
        expected_version: int,
        certification_code: str,
        certification_name: str,
        issued_date: date | None = None,
        expiry_date: date | None = None,
        certificate_number: str = "",
        issuer: str = "",
        notes: str = "",
    ) -> ResourceCertification:
        require_permission(
            self._user_session,
            "resource.manage",
            operation_label="update resource certification",
        )
        if self._cert_repo is None:
            raise RuntimeError("Certification repository is not configured.")
        existing = self._cert_repo.get(cert_id)
        if existing is None:
            raise NotFoundError("Certification not found.", code="CERT_NOT_FOUND")
        if existing.version != expected_version:
            raise ConcurrencyError(
                "Certification changed since you opened it.", code="STALE_WRITE"
            )
        candidate = replace(
            existing,
            certification_code=certification_code,
            certification_name=certification_name,
            issued_date=issued_date,
            expiry_date=expiry_date,
            certificate_number=certificate_number,
            issuer=issuer,
            notes=notes,
        )
        if self._cert_repo.code_exists(
            existing.resource_id,
            candidate.certification_code,
            exclude_id=existing.id,
        ):
            raise ValidationError(
                "This certification is already recorded for the resource.",
                code="RESOURCE_CERTIFICATION_DUPLICATE",
            )
        updated = self._cert_repo.update(candidate, expected_version=expected_version)
        self._stage_capability_activity(updated, action="resource.certification.updated")
        return updated

    def remove_resource_certification(
        self, cert_id: str, *, expected_version: int
    ) -> ResourceCertification:
        require_permission(
            self._user_session,
            "resource.manage",
            operation_label="remove resource certification",
        )
        if self._cert_repo is None:
            raise RuntimeError("Certification repository is not configured.")
        existing = self._cert_repo.get(cert_id)
        if existing is None:
            raise NotFoundError("Certification not found.", code="CERT_NOT_FOUND")
        if existing.version != expected_version:
            raise ConcurrencyError(
                "Certification changed since you opened it.", code="STALE_WRITE"
            )
        self._stage_capability_activity(existing, action="resource.certification.removed")
        self._cert_repo.delete(cert_id, expected_version=expected_version)
        return existing


__all__ = ["SkillCommandMixin"]
