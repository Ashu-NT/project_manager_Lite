from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from src.core.modules.project_management.domain.resources.skills import (
    ResourceCertification,
    ResourceSkill,
    SkillProficiencyLevel,
    SkillValidationMode,
    TaskSkillRequirement,
)
from src.core.modules.project_management.contracts.repositories.skills import (
    ResourceCertificationRepository,
    ResourceSkillRepository,
    TaskSkillRequirementRepository,
)
from src.core.modules.project_management.domain.tasks.task import Task
from src.core.platform.common.exceptions import BusinessRuleError


@dataclass
class SkillViolation:
    requirement_id: str
    task_id: str
    resource_id: str
    violation_type: str             # "missing_skill" | "insufficient_proficiency" | "expired_certification" | "missing_certification"
    skill_code: str | None
    certification_code: str | None
    required_proficiency: SkillProficiencyLevel | None
    actual_proficiency: SkillProficiencyLevel | None
    expiry_date: date | None
    message: str
    validation_mode: SkillValidationMode


@dataclass
class AssignmentValidationResult:
    """
    Outcome of skill/certification checks for a single resource-to-task assignment.

    Callers must inspect .can_assign and .requires_approval before persisting.
    """
    task_id: str
    resource_id: str
    violations: list[SkillViolation] = field(default_factory=list)
    warnings: list[SkillViolation] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """True when no BLOCK-mode violations exist."""
        return not self.violations

    @property
    def can_assign(self) -> bool:
        return self.is_valid or self.requires_approval

    @property
    def requires_approval(self) -> bool:
        """True when at least one OVERRIDE-mode violation exists (and no BLOCK violations)."""
        return (
            self.is_valid is False
            and all(v.validation_mode == SkillValidationMode.OVERRIDE for v in self.violations)
        )

    @property
    def is_blocked(self) -> bool:
        return any(v.validation_mode == SkillValidationMode.BLOCK for v in self.violations)

    def summary(self) -> str:
        parts: list[str] = []
        if self.violations:
            parts.append(f"{len(self.violations)} violation(s)")
        if self.warnings:
            parts.append(f"{len(self.warnings)} warning(s)")
        return "; ".join(parts) if parts else "valid"


class AssignmentSkillValidator:
    """
    Validates a resource-to-task assignment against the task's skill and
    certification requirements.

    Workflow integration:
        result = validator.validate(task, resource_id, planned_start, planned_finish)
        if result.is_blocked:
            raise BusinessRuleError(...)
        elif result.requires_approval:
            # route to platform approval with justification
        elif result.warnings:
            # record warnings in audit trail
    """

    def __init__(
        self,
        skill_repo: ResourceSkillRepository,
        cert_repo: ResourceCertificationRepository,
        requirement_repo: TaskSkillRequirementRepository,
    ) -> None:
        self._skills = skill_repo
        self._certs = cert_repo
        self._requirements = requirement_repo

    def list_requirements(self, task_id: str) -> list[TaskSkillRequirement]:
        return list(self._requirements.list_by_task(task_id or ""))

    def validate(
        self,
        task: Task,
        resource_id: str,
        planned_start: date | None = None,
        planned_finish: date | None = None,
    ) -> AssignmentValidationResult:
        """
        Check all skill/certification requirements for the task against the resource.

        planned_start/planned_finish are used for certification expiry checks.
        Falls back to task.start_date / task.end_date when not supplied.
        """
        result = AssignmentValidationResult(task_id=task.id, resource_id=resource_id)
        requirements = self._requirements.list_by_task(task.id)
        if not requirements:
            return result

        p_start = planned_start or task.start_date or date.today()
        p_finish = planned_finish or task.end_date or p_start

        resource_skills = {s.skill_code: s for s in self._skills.list_by_resource(resource_id)}
        resource_certs = {c.certification_code: c for c in self._certs.list_by_resource(resource_id)}

        for req in requirements:
            if req.is_skill_requirement:
                self._check_skill(req, resource_skills, result)
            elif req.is_certification_requirement:
                self._check_certification(req, resource_certs, p_start, p_finish, result)

        return result

    # ── per-requirement checks ───────────────────────────────────────────────

    def _check_skill(
        self,
        req: TaskSkillRequirement,
        resource_skills: dict[str, ResourceSkill],
        result: AssignmentValidationResult,
    ) -> None:
        skill = resource_skills.get(req.skill_code or "")
        if skill is None:
            violation = SkillViolation(
                requirement_id=req.id,
                task_id=req.task_id,
                resource_id=result.resource_id,
                violation_type="missing_skill",
                skill_code=req.skill_code,
                certification_code=None,
                required_proficiency=req.required_proficiency,
                actual_proficiency=None,
                expiry_date=None,
                message=(
                    f"Resource does not hold required skill '{req.skill_code}' "
                    f"(required: {req.required_proficiency.value})."
                ),
                validation_mode=req.validation_mode,
            )
        elif not skill.satisfies(req.required_proficiency):
            violation = SkillViolation(
                requirement_id=req.id,
                task_id=req.task_id,
                resource_id=result.resource_id,
                violation_type="insufficient_proficiency",
                skill_code=req.skill_code,
                certification_code=None,
                required_proficiency=req.required_proficiency,
                actual_proficiency=skill.proficiency,
                expiry_date=None,
                message=(
                    f"Resource skill '{req.skill_code}' is at {skill.proficiency.value} "
                    f"but task requires {req.required_proficiency.value}."
                ),
                validation_mode=req.validation_mode,
            )
        else:
            return  # passes

        self._bucket(violation, result)

    def _check_certification(
        self,
        req: TaskSkillRequirement,
        resource_certs: dict[str, ResourceCertification],
        planned_start: date,
        planned_finish: date,
        result: AssignmentValidationResult,
    ) -> None:
        cert = resource_certs.get(req.certification_code or "")
        if cert is None:
            violation = SkillViolation(
                requirement_id=req.id,
                task_id=req.task_id,
                resource_id=result.resource_id,
                violation_type="missing_certification",
                skill_code=None,
                certification_code=req.certification_code,
                required_proficiency=None,
                actual_proficiency=None,
                expiry_date=None,
                message=f"Resource does not hold required certification '{req.certification_code}'.",
                validation_mode=req.validation_mode,
            )
        elif not cert.is_valid_during(planned_start, planned_finish):
            violation = SkillViolation(
                requirement_id=req.id,
                task_id=req.task_id,
                resource_id=result.resource_id,
                violation_type="expired_certification",
                skill_code=None,
                certification_code=req.certification_code,
                required_proficiency=None,
                actual_proficiency=None,
                expiry_date=cert.expiry_date,
                message=(
                    f"Certification '{req.certification_code}' expires {cert.expiry_date} "
                    f"but task runs until {planned_finish}."
                ),
                validation_mode=req.validation_mode,
            )
        else:
            return  # passes

        self._bucket(violation, result)

    def _bucket(self, violation: SkillViolation, result: AssignmentValidationResult) -> None:
        if violation.validation_mode == SkillValidationMode.WARN:
            result.warnings.append(violation)
        else:
            result.violations.append(violation)


__all__ = [
    "AssignmentValidationResult",
    "AssignmentSkillValidator",
    "SkillViolation",
]
