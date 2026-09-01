"""Skill and certification command methods for ResourceService."""

from __future__ import annotations

from dataclasses import replace
from datetime import date

from src.core.modules.project_management.application.resources.resource_capability_events import (
    ResourceCapabilityChangeType,
    ResourceCapabilityChanged,
)
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
from src.core.shared.audit import record_audit_entry


class SkillCommandMixin:
    _skill_repo: ResourceSkillRepository | None
    _cert_repo: ResourceCertificationRepository | None

    def _stage_capability_activity(self, uow, child, *, action: str) -> None:
        record_activity(
            uow,
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

    def _record_resource_capability_event(
        self, uow, child, *, change_type: ResourceCapabilityChangeType
    ) -> None:
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="mutate resource capability"
        )
        uow.record_event(
            ResourceCapabilityChanged(
                tenant_id=scope.tenant_id,
                organization_id=scope.organization_id,
                resource_id=child.resource_id,
                child_id=child.id,
                child_version=child.version,
                child_type=type(child).__name__,
                change_type=change_type,
            )
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

        with self._require_uow_factory().create(context=self._new_context()) as uow:
            created = uow.skills.add(skill)
            self._stage_capability_activity(uow, created, action="resource.skill.added")
            record_audit_entry(
                uow,
                operation="create",
                entity_type="resource_skill",
                entity_id=created.id,
                module="project_management",
                severity="low",
                metadata={
                    "action": "resource.skill.added",
                    "resource_id": created.resource_id,
                    "skill_code": created.skill_code,
                },
                commit=False,
                fail_closed=True,
            )
            self._record_resource_capability_event(
                uow, created, change_type=ResourceCapabilityChangeType.ADDED
            )
            uow.commit()
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
        if candidate == existing:
            # True no-op (P18A §10): zero repository write, zero audit, zero typed event, zero
            # legacy signal, no synthetic version bump.
            return existing
        if self._skill_repo.code_exists(
            existing.resource_id, candidate.skill_code, exclude_id=existing.id
        ):
            raise ValidationError(
                "This skill is already recorded for the resource.",
                code="RESOURCE_SKILL_DUPLICATE",
            )

        with self._require_uow_factory().create(context=self._new_context()) as uow:
            updated = uow.skills.update(candidate, expected_version=expected_version)
            self._stage_capability_activity(uow, updated, action="resource.skill.updated")
            record_audit_entry(
                uow,
                operation="update",
                entity_type="resource_skill",
                entity_id=updated.id,
                module="project_management",
                severity="low",
                metadata={
                    "action": "resource.skill.updated",
                    "resource_id": updated.resource_id,
                    "skill_code": updated.skill_code,
                },
                commit=False,
                fail_closed=True,
            )
            self._record_resource_capability_event(
                uow, updated, change_type=ResourceCapabilityChangeType.UPDATED
            )
            uow.commit()
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

        with self._require_uow_factory().create(context=self._new_context()) as uow:
            uow.skills.delete(skill_id, expected_version=expected_version)
            self._stage_capability_activity(uow, existing, action="resource.skill.removed")
            record_audit_entry(
                uow,
                operation="delete",
                entity_type="resource_skill",
                entity_id=existing.id,
                module="project_management",
                severity="low",
                metadata={
                    "action": "resource.skill.removed",
                    "resource_id": existing.resource_id,
                    "skill_code": existing.skill_code,
                },
                commit=False,
                fail_closed=True,
            )
            self._record_resource_capability_event(
                uow, existing, change_type=ResourceCapabilityChangeType.REMOVED
            )
            uow.commit()
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

        with self._require_uow_factory().create(context=self._new_context()) as uow:
            created = uow.certifications.add(cert)
            self._stage_capability_activity(uow, created, action="resource.certification.added")
            record_audit_entry(
                uow,
                operation="create",
                entity_type="resource_certification",
                entity_id=created.id,
                module="project_management",
                severity="low",
                metadata={
                    "action": "resource.certification.added",
                    "resource_id": created.resource_id,
                    "certification_code": created.certification_code,
                },
                commit=False,
                fail_closed=True,
            )
            self._record_resource_capability_event(
                uow, created, change_type=ResourceCapabilityChangeType.ADDED
            )
            uow.commit()
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
        if candidate == existing:
            # True no-op (P18A §10).
            return existing
        if self._cert_repo.code_exists(
            existing.resource_id,
            candidate.certification_code,
            exclude_id=existing.id,
        ):
            raise ValidationError(
                "This certification is already recorded for the resource.",
                code="RESOURCE_CERTIFICATION_DUPLICATE",
            )

        with self._require_uow_factory().create(context=self._new_context()) as uow:
            updated = uow.certifications.update(candidate, expected_version=expected_version)
            self._stage_capability_activity(uow, updated, action="resource.certification.updated")
            record_audit_entry(
                uow,
                operation="update",
                entity_type="resource_certification",
                entity_id=updated.id,
                module="project_management",
                severity="low",
                metadata={
                    "action": "resource.certification.updated",
                    "resource_id": updated.resource_id,
                    "certification_code": updated.certification_code,
                },
                commit=False,
                fail_closed=True,
            )
            self._record_resource_capability_event(
                uow, updated, change_type=ResourceCapabilityChangeType.UPDATED
            )
            uow.commit()
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

        with self._require_uow_factory().create(context=self._new_context()) as uow:
            uow.certifications.delete(cert_id, expected_version=expected_version)
            self._stage_capability_activity(uow, existing, action="resource.certification.removed")
            record_audit_entry(
                uow,
                operation="delete",
                entity_type="resource_certification",
                entity_id=existing.id,
                module="project_management",
                severity="low",
                metadata={
                    "action": "resource.certification.removed",
                    "resource_id": existing.resource_id,
                    "certification_code": existing.certification_code,
                },
                commit=False,
                fail_closed=True,
            )
            self._record_resource_capability_event(
                uow, existing, change_type=ResourceCapabilityChangeType.REMOVED
            )
            uow.commit()
        return existing


__all__ = ["SkillCommandMixin"]
