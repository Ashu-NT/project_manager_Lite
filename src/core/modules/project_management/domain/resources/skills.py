from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import field_validator, model_validator

from src.core.modules.project_management.domain.identifiers import generate_id
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)


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


class CertificationStatus(str, Enum):
    VALID = "valid"
    EXPIRING_SOON = "expiring-soon"
    EXPIRED = "expired"


def _normalize_optional_date(value: object) -> date | None:
    if value in (None, ""):
        return None
    if not isinstance(value, date) or isinstance(value, datetime):
        raise ValidationError(
            "Skill and certification dates must be valid dates.",
            code="RESOURCE_SKILL_DATE_INVALID",
        )
    return value


def _normalize_optional_code(value: object) -> str | None:
    normalized = normalize_optional_text(value).lower()
    return normalized or None


def _normalize_required_code(value: object, *, message: str, code: str) -> str:
    return normalize_required_text(value, message=message, code=code).lower()


def _normalize_positive_int(value: object, *, code: str, message: str) -> int:
    try:
        normalized = int(value if value not in (None, "") else 1)
    except (TypeError, ValueError) as exc:
        raise ValidationError(message, code=code) from exc
    if normalized < 1:
        raise ValidationError(message, code=code)
    return normalized


def _normalize_proficiency(
    value: object,
    *,
    code: str,
) -> SkillProficiencyLevel:
    if value in (None, ""):
        return SkillProficiencyLevel.INTERMEDIATE
    if isinstance(value, SkillProficiencyLevel):
        return value
    raw = normalize_optional_text(value).lower()
    try:
        return SkillProficiencyLevel(raw)
    except ValueError as exc:
        raise ValidationError(
            (
                "Skill proficiency must be one of: "
                f"{', '.join(level.value for level in SkillProficiencyLevel)}."
            ),
            code=code,
        ) from exc


def _normalize_validation_mode(value: object, *, code: str) -> SkillValidationMode:
    if value in (None, ""):
        return SkillValidationMode.WARN
    if isinstance(value, SkillValidationMode):
        return value
    raw = normalize_optional_text(value).lower()
    try:
        return SkillValidationMode(raw)
    except ValueError as exc:
        raise ValidationError(
            (
                "Skill validation mode must be one of: "
                f"{', '.join(mode.value for mode in SkillValidationMode)}."
            ),
            code=code,
        ) from exc


@validated_dataclass
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

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Resource skill ID is required.",
            code="RESOURCE_SKILL_ID_REQUIRED",
        )

    @field_validator("resource_id", mode="before")
    @classmethod
    def _validate_resource_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Resource ID is required.",
            code="RESOURCE_SKILL_RESOURCE_REQUIRED",
        )

    @field_validator("skill_code", mode="before")
    @classmethod
    def _validate_skill_code(cls, value: object) -> str:
        return _normalize_required_code(
            value,
            message="Skill code is required.",
            code="RESOURCE_SKILL_CODE_REQUIRED",
        )

    @field_validator("skill_name", mode="before")
    @classmethod
    def _validate_skill_name(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Skill name is required.",
            code="RESOURCE_SKILL_NAME_REQUIRED",
        )

    @field_validator("proficiency", mode="before")
    @classmethod
    def _validate_proficiency(cls, value: object) -> SkillProficiencyLevel:
        return _normalize_proficiency(
            value,
            code="RESOURCE_SKILL_PROFICIENCY_INVALID",
        )

    @field_validator("notes", mode="before")
    @classmethod
    def _normalize_notes(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return _normalize_positive_int(
            value,
            code="RESOURCE_SKILL_VERSION_INVALID",
            message="Resource skill version must be positive.",
        )

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


@validated_dataclass
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

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Resource certification ID is required.",
            code="RESOURCE_CERTIFICATION_ID_REQUIRED",
        )

    @field_validator("resource_id", mode="before")
    @classmethod
    def _validate_resource_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Resource ID is required.",
            code="RESOURCE_CERTIFICATION_RESOURCE_REQUIRED",
        )

    @field_validator("certification_code", mode="before")
    @classmethod
    def _validate_certification_code(cls, value: object) -> str:
        return _normalize_required_code(
            value,
            message="Certification code is required.",
            code="RESOURCE_CERTIFICATION_CODE_REQUIRED",
        )

    @field_validator("certification_name", mode="before")
    @classmethod
    def _validate_certification_name(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Certification name is required.",
            code="RESOURCE_CERTIFICATION_NAME_REQUIRED",
        )

    @field_validator("issued_date", "expiry_date", mode="before")
    @classmethod
    def _validate_dates(cls, value: object) -> date | None:
        return _normalize_optional_date(value)

    @field_validator("issuing_body", "notes", mode="before")
    @classmethod
    def _normalize_optional_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return _normalize_positive_int(
            value,
            code="RESOURCE_CERTIFICATION_VERSION_INVALID",
            message="Resource certification version must be positive.",
        )

    @model_validator(mode="after")
    def _validate_date_range(self) -> "ResourceCertification":
        if (
            self.issued_date is not None
            and self.expiry_date is not None
            and self.expiry_date < self.issued_date
        ):
            raise ValidationError(
                "Certification expiry date must be on or after issued date.",
                code="RESOURCE_CERTIFICATION_DATE_RANGE_INVALID",
            )
        return self

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

    def status_on(
        self,
        check_date: date,
        *,
        expiring_within_days: int = 30,
    ) -> CertificationStatus:
        """Return the certification lifecycle state on a given date."""
        if expiring_within_days < 0:
            raise ValueError("expiring_within_days cannot be negative")
        if self.expiry_date is None or (
            self.expiry_date - check_date
        ).days > expiring_within_days:
            return CertificationStatus.VALID
        if self.expiry_date < check_date:
            return CertificationStatus.EXPIRED
        return CertificationStatus.EXPIRING_SOON


@validated_dataclass
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

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Task skill requirement ID is required.",
            code="TASK_SKILL_REQUIREMENT_ID_REQUIRED",
        )

    @field_validator("task_id", mode="before")
    @classmethod
    def _validate_task_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Task ID is required.",
            code="TASK_SKILL_REQUIREMENT_TASK_REQUIRED",
        )

    @field_validator("skill_code", "certification_code", mode="before")
    @classmethod
    def _normalize_optional_codes(cls, value: object) -> str | None:
        return _normalize_optional_code(value)

    @field_validator("required_proficiency", mode="before")
    @classmethod
    def _validate_required_proficiency(cls, value: object) -> SkillProficiencyLevel:
        return _normalize_proficiency(
            value,
            code="TASK_SKILL_REQUIREMENT_PROFICIENCY_INVALID",
        )

    @field_validator("validation_mode", mode="before")
    @classmethod
    def _validate_validation_mode(cls, value: object) -> SkillValidationMode:
        return _normalize_validation_mode(
            value,
            code="TASK_SKILL_REQUIREMENT_MODE_INVALID",
        )

    @field_validator("notes", mode="before")
    @classmethod
    def _normalize_notes(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return _normalize_positive_int(
            value,
            code="TASK_SKILL_REQUIREMENT_VERSION_INVALID",
            message="Task skill requirement version must be positive.",
        )

    @model_validator(mode="after")
    def _validate_requirement_target(self) -> "TaskSkillRequirement":
        if self.skill_code is None and self.certification_code is None:
            raise ValidationError(
                "Task skill requirement requires either skill_code or certification_code.",
                code="TASK_SKILL_REQUIREMENT_TARGET_REQUIRED",
            )
        if self.skill_code is not None and self.certification_code is not None:
            raise ValidationError(
                "Task skill requirement cannot define both skill_code and certification_code.",
                code="TASK_SKILL_REQUIREMENT_TARGET_AMBIGUOUS",
            )
        return self

    @staticmethod
    def create(
        task_id: str,
        skill_code: str | None = None,
        certification_code: str | None = None,
        required_proficiency: SkillProficiencyLevel = SkillProficiencyLevel.INTERMEDIATE,
        validation_mode: SkillValidationMode = SkillValidationMode.WARN,
        notes: str = "",
    ) -> "TaskSkillRequirement":
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
    "CertificationStatus",
    "ResourceSkill",
    "ResourceCertification",
    "TaskSkillRequirement",
    "SkillProficiencyLevel",
    "SkillValidationMode",
]
