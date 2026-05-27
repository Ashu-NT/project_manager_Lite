"""Mappers between skill/cert domain objects and ORM rows."""

from __future__ import annotations

from src.core.modules.project_management.domain.resources.skills import (
    ResourceCertification,
    ResourceSkill,
    SkillProficiencyLevel,
)
from src.core.modules.project_management.infrastructure.persistence.orm.skills import (
    ResourceCertificationORM,
    ResourceSkillORM,
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


__all__ = ["cert_from_orm", "cert_to_orm", "skill_from_orm", "skill_to_orm"]
