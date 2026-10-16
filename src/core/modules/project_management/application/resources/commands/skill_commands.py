"""Governed skill and certification commands."""

from __future__ import annotations

from dataclasses import replace
from typing import cast

from src.core.modules.project_management.application.resources.catalog.resource_capability_events import (
    ResourceCapabilityChanged,
    ResourceCapabilityChangeType,
)
from src.core.modules.project_management.application.resources.dto.commands.certifications import (
    ResourceAddCertificationCommand,
    ResourceRemoveCertificationCommand,
    ResourceUpdateCertificationCommand,
)
from src.core.modules.project_management.application.resources.dto.commands.skills import (
    ResourceAddSkillCommand,
    ResourceRemoveSkillCommand,
    ResourceUpdateSkillCommand,
)
from src.core.modules.project_management.application.resources.dto.responses.capabilities import (
    ResourceCertificationResponse,
    ResourceSkillResponse,
)
from src.core.modules.project_management.application.resources.mappers.capabilities import (
    map_resource_certification,
    map_resource_skill,
)
from src.core.modules.project_management.application.resources.normalization import (
    parse_certification_date,
)
from src.core.modules.project_management.contracts.repositories.resources.skills import (
    ResourceCertificationRepository,
    ResourceSkillRepository,
)
from src.core.modules.project_management.contracts.uow.resources.resource_unit_of_work import (
    ResourceUnitOfWorkFactory,
)
from src.core.modules.project_management.domain.resources.skills import (
    ResourceCertification,
    ResourceSkill,
    SkillProficiencyLevel,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import (
    ConcurrencyError,
    ConfigurationError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.common.ids import generate_id
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry
from src.core.shared.events.domain_event_context import DomainEventContext


class ResourceCapabilityCommandHandler:
    def __init__(
        self,
        *,
        skill_repo: ResourceSkillRepository | None,
        cert_repo: ResourceCertificationRepository | None,
        user_session: UserSessionContext | None,
        tenant_context_service: TenantContextService | None,
        uow_factory: ResourceUnitOfWorkFactory | None,
    ) -> None:
        self._skill_repo = skill_repo
        self._cert_repo = cert_repo
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service
        self._uow_factory = uow_factory

    def _require_uow_factory(self) -> ResourceUnitOfWorkFactory:
        if self._uow_factory is None:
            raise ConfigurationError("Resource unit of work is not configured.")
        return self._uow_factory

    def _new_context(self, *, causation_id: str | None = None) -> DomainEventContext:
        return DomainEventContext(correlation_id=generate_id(), causation_id=causation_id)

    def _stage_capability_audit(self, uow, child, *, operation: str, action: str) -> None:
        record_audit_entry(
            uow,
            operation=operation,
            entity_type="resource",
            entity_id=child.resource_id,
            module="project_management",
            category="MASTER_DATA",
            severity="low",
            metadata={"action": action, "child_id": child.id, "capability_type": type(child).__name__},
            commit=False,
            fail_closed=True,
        )

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
        if self._tenant_context_service is None:
            raise ConfigurationError("Resource capability tenant scope is not configured.")
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

    def add_resource_skill(self, command: ResourceAddSkillCommand) -> ResourceSkillResponse:
        require_permission(
            self._user_session, "resource.manage", operation_label="add resource skill"
        )
        if self._skill_repo is None:
            raise ConfigurationError("Skill repository is not configured.")
        # The validated domain dataclass normalizes text to SkillProficiencyLevel.
        skill = ResourceSkill.create(
            resource_id=command.resource_id,
            skill_code=command.skill_code,
            skill_name=command.skill_name,
            proficiency=cast(SkillProficiencyLevel, command.proficiency),
            notes=command.notes,
        )
        if self._skill_repo.code_exists(command.resource_id, skill.skill_code):
            raise ValidationError(
                "This skill is already recorded for the resource.",
                code="RESOURCE_SKILL_DUPLICATE",
            )

        with self._require_uow_factory().create(context=self._new_context()) as uow:
            created = uow.skills.add(skill)
            self._stage_capability_audit(uow, created, operation="create", action="resource.skill.added")
            self._stage_capability_activity(uow, created, action="resource.skill.added")
            self._record_resource_capability_event(
                uow, created, change_type=ResourceCapabilityChangeType.ADDED
            )
            uow.commit()
        return map_resource_skill(created)

    def update_resource_skill(self, command: ResourceUpdateSkillCommand) -> ResourceSkillResponse:
        require_permission(
            self._user_session, "resource.manage", operation_label="update resource skill"
        )
        if self._skill_repo is None:
            raise ConfigurationError("Skill repository is not configured.")
        existing = self._skill_repo.get(command.skill_id)
        if existing is None:
            raise NotFoundError("Skill not found.", code="SKILL_NOT_FOUND")
        if existing.version != command.expected_version:
            raise ConcurrencyError(
                "Skill changed since you opened it.", code="STALE_WRITE"
            )
        candidate = replace(
            existing,
            skill_code=command.skill_code,
            skill_name=command.skill_name,
            proficiency=cast(SkillProficiencyLevel, command.proficiency),
            notes=command.notes,
        )
        if candidate == existing:
            # True no-op: no write, audit, event, or version bump.
            return map_resource_skill(existing)
        if self._skill_repo.code_exists(
            existing.resource_id, candidate.skill_code, exclude_id=existing.id
        ):
            raise ValidationError(
                "This skill is already recorded for the resource.",
                code="RESOURCE_SKILL_DUPLICATE",
            )

        with self._require_uow_factory().create(context=self._new_context()) as uow:
            updated = uow.skills.update(candidate, expected_version=command.expected_version)
            self._stage_capability_audit(uow, updated, operation="update", action="resource.skill.updated")
            self._stage_capability_activity(uow, updated, action="resource.skill.updated")
            self._record_resource_capability_event(
                uow, updated, change_type=ResourceCapabilityChangeType.UPDATED
            )
            uow.commit()
        return map_resource_skill(updated)

    def remove_resource_skill(self, command: ResourceRemoveSkillCommand) -> ResourceSkillResponse:
        require_permission(
            self._user_session, "resource.manage", operation_label="remove resource skill"
        )
        if self._skill_repo is None:
            raise ConfigurationError("Skill repository is not configured.")
        existing = self._skill_repo.get(command.skill_id)
        if existing is None:
            raise NotFoundError("Skill not found.", code="SKILL_NOT_FOUND")
        if existing.version != command.expected_version:
            raise ConcurrencyError(
                "Skill changed since you opened it.", code="STALE_WRITE"
            )

        with self._require_uow_factory().create(context=self._new_context()) as uow:
            uow.skills.delete(command.skill_id, expected_version=command.expected_version)
            self._stage_capability_audit(uow, existing, operation="delete", action="resource.skill.removed")
            self._stage_capability_activity(uow, existing, action="resource.skill.removed")
            self._record_resource_capability_event(
                uow, existing, change_type=ResourceCapabilityChangeType.REMOVED
            )
            uow.commit()
        return map_resource_skill(existing)

    def add_resource_certification(self, command: ResourceAddCertificationCommand) -> ResourceCertificationResponse:
        issued_date = parse_certification_date(command.issued_date)
        expiry_date = parse_certification_date(command.expiry_date)
        require_permission(
            self._user_session,
            "resource.manage",
            operation_label="add resource certification",
        )
        if self._cert_repo is None:
            raise ConfigurationError("Certification repository is not configured.")
        cert = ResourceCertification.create(
            resource_id=command.resource_id,
            certification_code=command.certification_code,
            certification_name=command.certification_name,
            issued_date=issued_date,
            expiry_date=expiry_date,
            certificate_number=command.certificate_number,
            issuer=command.issuer,
            notes=command.notes,
        )
        if self._cert_repo.code_exists(command.resource_id, cert.certification_code):
            raise ValidationError(
                "This certification is already recorded for the resource.",
                code="RESOURCE_CERTIFICATION_DUPLICATE",
            )

        with self._require_uow_factory().create(context=self._new_context()) as uow:
            created = uow.certifications.add(cert)
            self._stage_capability_audit(uow, created, operation="create", action="resource.certification.added")
            self._stage_capability_activity(uow, created, action="resource.certification.added")
            self._record_resource_capability_event(
                uow, created, change_type=ResourceCapabilityChangeType.ADDED
            )
            uow.commit()
        return map_resource_certification(created)

    def update_resource_certification(self, command: ResourceUpdateCertificationCommand) -> ResourceCertificationResponse:
        issued_date = parse_certification_date(command.issued_date)
        expiry_date = parse_certification_date(command.expiry_date)
        require_permission(
            self._user_session,
            "resource.manage",
            operation_label="update resource certification",
        )
        if self._cert_repo is None:
            raise ConfigurationError("Certification repository is not configured.")
        existing = self._cert_repo.get(command.cert_id)
        if existing is None:
            raise NotFoundError("Certification not found.", code="CERT_NOT_FOUND")
        if existing.version != command.expected_version:
            raise ConcurrencyError(
                "Certification changed since you opened it.", code="STALE_WRITE"
            )
        candidate = replace(
            existing,
            certification_code=command.certification_code,
            certification_name=command.certification_name,
            issued_date=issued_date,
            expiry_date=expiry_date,
            certificate_number=command.certificate_number,
            issuer=command.issuer,
            notes=command.notes,
        )
        if candidate == existing:
            # True no-op.
            return map_resource_certification(existing)
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
            updated = uow.certifications.update(candidate, expected_version=command.expected_version)
            self._stage_capability_audit(uow, updated, operation="update", action="resource.certification.updated")
            self._stage_capability_activity(uow, updated, action="resource.certification.updated")
            self._record_resource_capability_event(
                uow, updated, change_type=ResourceCapabilityChangeType.UPDATED
            )
            uow.commit()
        return map_resource_certification(updated)

    def remove_resource_certification(self, command: ResourceRemoveCertificationCommand) -> ResourceCertificationResponse:
        require_permission(
            self._user_session,
            "resource.manage",
            operation_label="remove resource certification",
        )
        if self._cert_repo is None:
            raise ConfigurationError("Certification repository is not configured.")
        existing = self._cert_repo.get(command.cert_id)
        if existing is None:
            raise NotFoundError("Certification not found.", code="CERT_NOT_FOUND")
        if existing.version != command.expected_version:
            raise ConcurrencyError(
                "Certification changed since you opened it.", code="STALE_WRITE"
            )

        with self._require_uow_factory().create(context=self._new_context()) as uow:
            uow.certifications.delete(command.cert_id, expected_version=command.expected_version)
            self._stage_capability_audit(uow, existing, operation="delete", action="resource.certification.removed")
            self._stage_capability_activity(uow, existing, action="resource.certification.removed")
            self._record_resource_capability_event(
                uow, existing, change_type=ResourceCapabilityChangeType.REMOVED
            )
            uow.commit()
        return map_resource_certification(existing)


__all__ = ["ResourceCapabilityCommandHandler"]
