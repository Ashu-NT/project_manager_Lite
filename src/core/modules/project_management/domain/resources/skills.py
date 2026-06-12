from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from src.core.modules.project_management.domain.identifiers import generate_id


class SkillProficiencyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class SkillValidationMode(str, Enum):
    """Controls how a missing or expired skill/cert is handled during assignment."""
    WARN = "warn"       # record warning, allow assignment
    BLOCK = "block"     # prevent assignment until resolved
    OVERRIDE = "override"  # allow with approval + recorded justification


@dataclass
class ResourceSkill:
    """
    Declares that a resource holds a particular skill at a given proficiency level.

    Skills do not expire; certifications (ResourceCertification) have validity dates.
    """
    id: str
    resource_id: str
    skill_code: str          # canonical skill identifier (e.g. "welding.1g", "python.advanced")
    skill_name: str
    proficiency: SkillProficiencyLevel = SkillProficiencyLevel.INTERMEDIATE
    notes: str = ""
    version: int = 1

    @staticmethod
    def create(
        resource_id: str,
        skill_code: str,
        skill_name: str,
        proficiency: SkillProficiencyLevel = SkillProficiencyLevel.INTERMEDIATE,
        notes: str = "",
    ) -> "ResourceSkill":
        return ResourceSkill(
            id=generate_id(),
            resource_id=resource_id,
            skill_code=skill_code,
            skill_name=skill_name,
            proficiency=proficiency,
            notes=notes,
        )

    def satisfies(self, required_proficiency: SkillProficiencyLevel) -> bool:
        """Return True if this skill meets or exceeds the required proficiency."""
        order = list(SkillProficiencyLevel)
        return order.index(self.proficiency) >= order.index(required_proficiency)


@dataclass
class ResourceCertification:
    """
    A time-bounded certification held by a resource.

    Expiry is checked against the planned task date window during assignment
    validation — an expired cert within the planned window triggers a violation.
    """
    id: str
    resource_id: str
    certification_code: str
    certification_name: str
    issued_date: date | None = None
    expiry_date: date | None = None
    issuing_body: str = ""
    notes: str = ""
    version: int = 1

    @staticmethod
    def create(
        resource_id: str,
        certification_code: str,
        certification_name: str,
        issued_date: date | None = None,
        expiry_date: date | None = None,
        issuing_body: str = "",
        notes: str = "",
    ) -> "ResourceCertification":
        return ResourceCertification(
            id=generate_id(),
            resource_id=resource_id,
            certification_code=certification_code,
            certification_name=certification_name,
            issued_date=issued_date,
            expiry_date=expiry_date,
            issuing_body=issuing_body,
            notes=notes,
        )

    def is_valid_on(self, check_date: date) -> bool:
        """Return True if the cert is not expired on check_date."""
        if self.expiry_date is None:
            return True
        return check_date <= self.expiry_date

    def is_valid_during(self, start: date, finish: date) -> bool:
        """Return True if the cert remains valid throughout the entire date window."""
        if self.expiry_date is None:
            return True
        return finish <= self.expiry_date


@dataclass
class TaskSkillRequirement:
    """
    Declares that a task requires a resource with a specific skill or certification.

    validation_mode controls what happens when the assigned resource lacks the skill:
        WARN    — allow but record a warning
        BLOCK   — prevent assignment
        OVERRIDE — allow with approval and justification
    """
    id: str
    task_id: str
    skill_code: str | None = None             # required skill (if skill-based)
    certification_code: str | None = None      # required cert (if cert-based)
    required_proficiency: SkillProficiencyLevel = SkillProficiencyLevel.INTERMEDIATE
    validation_mode: SkillValidationMode = SkillValidationMode.WARN
    notes: str = ""
    version: int = 1

    @staticmethod
    def create(
        task_id: str,
        skill_code: str | None = None,
        certification_code: str | None = None,
        required_proficiency: SkillProficiencyLevel = SkillProficiencyLevel.INTERMEDIATE,
        validation_mode: SkillValidationMode = SkillValidationMode.WARN,
        notes: str = "",
    ) -> "TaskSkillRequirement":
        if skill_code is None and certification_code is None:
            raise ValueError("TaskSkillRequirement requires either skill_code or certification_code.")
        return TaskSkillRequirement(
            id=generate_id(),
            task_id=task_id,
            skill_code=skill_code,
            certification_code=certification_code,
            required_proficiency=required_proficiency,
            validation_mode=validation_mode,
            notes=notes,
        )

    @property
    def is_skill_requirement(self) -> bool:
        return self.skill_code is not None

    @property
    def is_certification_requirement(self) -> bool:
        return self.certification_code is not None


__all__ = [
    "ResourceSkill",
    "ResourceCertification",
    "TaskSkillRequirement",
    "SkillProficiencyLevel",
    "SkillValidationMode",
]
