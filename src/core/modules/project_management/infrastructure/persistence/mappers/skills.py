"""Mappers between skill/cert domain objects and ORM rows."""

from __future__ import annotations

from src.core.modules.project_management.domain.resources.skills import (
    ResourceCertification,
    ResourceSkill,
    SkillProficiencyLevel,
    SkillValidationMode,
    TaskSkillRequirement,
)
from src.core.modules.project_management.infrastructure.persistence.orm.skills import (
    ResourceCertificationORM,
    ResourceSkillORM,
    TaskSkillRequirementORM,
)


def skill_to_orm(skill: ResourceSkill) -> ResourceSkillORM:
    return ResourceSkillORM(
        id=skill.id,
        resource_id=skill.resource_id,
        skill_code=skill.skill_code,
        skill_name=skill.skill_name,
        proficiency=skill.proficiency.value
        if isinstance(skill.proficiency, SkillProficiencyLevel)
        else str(skill.proficiency or "intermediate"),
        notes=skill.notes or None,
        version=skill.version,
    )


def skill_from_orm(obj: ResourceSkillORM) -> ResourceSkill:
    proficiency_raw = str(obj.proficiency or "intermediate").lower()
    try:
        proficiency = SkillProficiencyLevel(proficiency_raw)
    except ValueError:
        proficiency = SkillProficiencyLevel.INTERMEDIATE
    return ResourceSkill(
        id=obj.id,
        resource_id=obj.resource_id,
        skill_code=obj.skill_code,
        skill_name=obj.skill_name,
        proficiency=proficiency,
        notes=obj.notes or "",
        version=obj.version,
    )


def cert_to_orm(cert: ResourceCertification) -> ResourceCertificationORM:
    return ResourceCertificationORM(
        id=cert.id,
        resource_id=cert.resource_id,
        certification_code=cert.certification_code,
        certification_name=cert.certification_name,
        issued_date=cert.issued_date,
        expiry_date=cert.expiry_date,
        issuing_authority=cert.issuing_body or None,
        notes=cert.notes or None,
        version=cert.version,
    )


def cert_from_orm(obj: ResourceCertificationORM) -> ResourceCertification:
    return ResourceCertification(
        id=obj.id,
        resource_id=obj.resource_id,
        certification_code=obj.certification_code,
        certification_name=obj.certification_name,
        issued_date=obj.issued_date,
        expiry_date=obj.expiry_date,
        issuing_body=obj.issuing_authority or "",
        notes=obj.notes or "",
        version=obj.version,
    )


def task_req_to_orm(req: TaskSkillRequirement) -> TaskSkillRequirementORM:
    return TaskSkillRequirementORM(
        id=req.id,
        task_id=req.task_id,
        skill_code=req.skill_code or None,
        certification_code=req.certification_code or None,
        required_proficiency=(
            req.required_proficiency.value
            if isinstance(req.required_proficiency, SkillProficiencyLevel)
            else str(req.required_proficiency or "intermediate")
        ),
        validation_mode=(
            req.validation_mode.value
            if isinstance(req.validation_mode, SkillValidationMode)
            else str(req.validation_mode or "warn")
        ),
        notes=req.notes or None,
        version=req.version,
    )


def task_req_from_orm(obj: TaskSkillRequirementORM) -> TaskSkillRequirement:
    proficiency_raw = str(obj.required_proficiency or "intermediate").lower()
    try:
        proficiency = SkillProficiencyLevel(proficiency_raw)
    except ValueError:
        proficiency = SkillProficiencyLevel.INTERMEDIATE
    mode_raw = str(obj.validation_mode or "warn").lower()
    try:
        validation_mode = SkillValidationMode(mode_raw)
    except ValueError:
        validation_mode = SkillValidationMode.WARN
    return TaskSkillRequirement(
        id=obj.id,
        task_id=obj.task_id,
        skill_code=obj.skill_code or None,
        certification_code=obj.certification_code or None,
        required_proficiency=proficiency,
        validation_mode=validation_mode,
        notes=obj.notes or "",
        version=obj.version,
    )


__all__ = [
    "cert_from_orm",
    "cert_to_orm",
    "skill_from_orm",
    "skill_to_orm",
    "task_req_from_orm",
    "task_req_to_orm",
]
