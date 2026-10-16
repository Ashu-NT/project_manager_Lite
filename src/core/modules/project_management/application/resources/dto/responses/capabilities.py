from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.core.modules.project_management.domain.resources.skills import (
    SkillProficiencyLevel,
)


@dataclass(frozen=True, slots=True)
class ResourceSkillResponse:
    id: str
    resource_id: str
    skill_code: str
    skill_name: str
    proficiency: SkillProficiencyLevel = SkillProficiencyLevel.INTERMEDIATE
    notes: str = ""
    version: int = 1


@dataclass(frozen=True, slots=True)
class ResourceCertificationResponse:
    id: str
    resource_id: str
    certification_code: str
    certification_name: str
    issued_date: date | None = None
    expiry_date: date | None = None
    certificate_number: str = ""
    issuer: str = ""
    notes: str = ""
    version: int = 1
    cert_status: str = "no-expiry"








