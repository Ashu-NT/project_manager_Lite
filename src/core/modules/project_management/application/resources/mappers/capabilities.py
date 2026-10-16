from __future__ import annotations

from datetime import date

from src.core.modules.project_management.application.resources.dto.responses.capabilities import (
    ResourceCertificationResponse,
    ResourceSkillResponse,
)
from src.core.modules.project_management.domain.resources.skills import (
    ResourceCertification,
    ResourceSkill,
)


def map_resource_skill(value: ResourceSkill) -> ResourceSkillResponse:
    return ResourceSkillResponse(
        id=value.id,
        resource_id=value.resource_id,
        skill_code=value.skill_code,
        skill_name=value.skill_name,
        proficiency=value.proficiency,
        notes=value.notes,
        version=value.version,
    )


def map_resource_certification(value: ResourceCertification) -> ResourceCertificationResponse:
    return ResourceCertificationResponse(
        id=value.id,
        resource_id=value.resource_id,
        certification_code=value.certification_code,
        certification_name=value.certification_name,
        issued_date=value.issued_date,
        expiry_date=value.expiry_date,
        certificate_number=value.certificate_number,
        issuer=value.issuer,
        notes=value.notes,
        version=value.version,
        cert_status=value.status_on(date.today()).value,
    )








