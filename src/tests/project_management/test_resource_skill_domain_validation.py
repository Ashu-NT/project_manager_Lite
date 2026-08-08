from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from src.core.modules.project_management.application.resources.resource_service import (
    ResourceService,
)
from src.core.modules.project_management.domain.resources.skills import (
    CertificationStatus,
    ResourceCertification,
    ResourceSkill,
    SkillProficiencyLevel,
    SkillValidationMode,
    TaskSkillRequirement,
)
from src.core.platform.common.exceptions import ValidationError


class _RecordingSkillRepo:
    def __init__(self) -> None:
        self.added: list[ResourceSkill] = []

    def add(self, skill: ResourceSkill) -> ResourceSkill:
        self.added.append(skill)
        return skill

    def get(self, skill_id: str) -> ResourceSkill | None:
        return next((skill for skill in self.added if skill.id == skill_id), None)

    def list_by_resource(self, resource_id: str) -> list[ResourceSkill]:
        return [skill for skill in self.added if skill.resource_id == resource_id]

    def delete(self, skill_id: str) -> None:
        self.added = [skill for skill in self.added if skill.id != skill_id]


class _RecordingCertRepo:
    def __init__(self) -> None:
        self.added: list[ResourceCertification] = []

    def add(self, cert: ResourceCertification) -> ResourceCertification:
        self.added.append(cert)
        return cert

    def get(self, cert_id: str) -> ResourceCertification | None:
        return next((cert for cert in self.added if cert.id == cert_id), None)

    def list_by_resource(self, resource_id: str) -> list[ResourceCertification]:
        return [cert for cert in self.added if cert.resource_id == resource_id]

    def delete(self, cert_id: str) -> None:
        self.added = [cert for cert in self.added if cert.id != cert_id]


def _make_resource_service(
    *,
    skill_repo: _RecordingSkillRepo | None = None,
    cert_repo: _RecordingCertRepo | None = None,
) -> ResourceService:
    return ResourceService(
        session=SimpleNamespace(),
        resource_repo=SimpleNamespace(),
        assignment_repo=SimpleNamespace(),
        skill_repo=skill_repo,
        cert_repo=cert_repo,
    )


def test_resource_skill_dto_normalizes_and_validates_fields() -> None:
    skill = ResourceSkill.create(
        resource_id="  res-1  ",
        skill_code="  PYTHON  ",
        skill_name="  Python  ",
        proficiency="ADVANCED",
        notes="  Core backend skill  ",
    )

    assert skill.resource_id == "res-1"
    assert skill.skill_code == "python"
    assert skill.skill_name == "Python"
    assert skill.proficiency == SkillProficiencyLevel.ADVANCED
    assert skill.notes == "Core backend skill"

    with pytest.raises(ValidationError) as exc_resource:
        ResourceSkill.create(
            resource_id=" ",
            skill_code="python",
            skill_name="Python",
        )
    assert exc_resource.value.code == "RESOURCE_SKILL_RESOURCE_REQUIRED"

    with pytest.raises(ValidationError) as exc_proficiency:
        ResourceSkill.create(
            resource_id="res-1",
            skill_code="python",
            skill_name="Python",
            proficiency="guru",
        )
    assert exc_proficiency.value.code == "RESOURCE_SKILL_PROFICIENCY_INVALID"


def test_resource_certification_dto_normalizes_and_validates_ranges() -> None:
    cert = ResourceCertification.create(
        resource_id="  res-1  ",
        certification_code="  PMP  ",
        certification_name="  Project Management Professional  ",
        issued_date=date(2026, 1, 1),
        expiry_date=date(2026, 12, 31),
        issuing_body="  PMI  ",
        notes="  Current cert  ",
    )

    assert cert.resource_id == "res-1"
    assert cert.certification_code == "pmp"
    assert cert.certification_name == "Project Management Professional"
    assert cert.issuing_body == "PMI"
    assert cert.notes == "Current cert"

    with pytest.raises(ValidationError) as exc_name:
        ResourceCertification.create(
            resource_id="res-1",
            certification_code="pmp",
            certification_name=" ",
        )
    assert exc_name.value.code == "RESOURCE_CERTIFICATION_NAME_REQUIRED"

    with pytest.raises(ValidationError) as exc_range:
        ResourceCertification.create(
            resource_id="res-1",
            certification_code="pmp",
            certification_name="PMP",
            issued_date=date(2026, 12, 31),
            expiry_date=date(2026, 1, 1),
        )
    assert exc_range.value.code == "RESOURCE_CERTIFICATION_DATE_RANGE_INVALID"


def test_resource_certification_owns_lifecycle_status_boundaries() -> None:
    as_of = date(2026, 6, 1)

    def certification(expiry_date: date | None) -> ResourceCertification:
        return ResourceCertification.create(
            resource_id="res-1",
            certification_code="pmp",
            certification_name="PMP",
            expiry_date=expiry_date,
        )

    assert certification(None).status_on(as_of) == CertificationStatus.VALID
    assert certification(date(2026, 5, 31)).status_on(as_of) == CertificationStatus.EXPIRED
    assert (
        certification(date(2026, 6, 1)).status_on(as_of)
        == CertificationStatus.EXPIRING_SOON
    )
    assert (
        certification(date(2026, 7, 1)).status_on(as_of)
        == CertificationStatus.EXPIRING_SOON
    )
    assert certification(date(2026, 7, 2)).status_on(as_of) == CertificationStatus.VALID

    with pytest.raises(ValueError, match="cannot be negative"):
        certification(None).status_on(as_of, expiring_within_days=-1)


def test_task_skill_requirement_dto_normalizes_and_validates_shape() -> None:
    skill_requirement = TaskSkillRequirement.create(
        task_id="  task-1  ",
        skill_code="  PYTHON  ",
        required_proficiency="EXPERT",
        validation_mode="BLOCK",
        notes="  Critical path  ",
    )
    cert_requirement = TaskSkillRequirement.create(
        task_id="task-2",
        certification_code="  SAFETY  ",
        required_proficiency="INTERMEDIATE",
        validation_mode="OVERRIDE",
    )

    assert skill_requirement.task_id == "task-1"
    assert skill_requirement.skill_code == "python"
    assert skill_requirement.certification_code is None
    assert skill_requirement.required_proficiency == SkillProficiencyLevel.EXPERT
    assert skill_requirement.validation_mode == SkillValidationMode.BLOCK
    assert skill_requirement.notes == "Critical path"
    assert skill_requirement.is_skill_requirement is True

    assert cert_requirement.skill_code is None
    assert cert_requirement.certification_code == "safety"
    assert cert_requirement.validation_mode == SkillValidationMode.OVERRIDE
    assert cert_requirement.is_certification_requirement is True

    with pytest.raises(ValidationError) as exc_missing:
        TaskSkillRequirement.create(task_id="task-1")
    assert exc_missing.value.code == "TASK_SKILL_REQUIREMENT_TARGET_REQUIRED"

    with pytest.raises(ValidationError) as exc_ambiguous:
        TaskSkillRequirement.create(
            task_id="task-1",
            skill_code="python",
            certification_code="safety",
        )
    assert exc_ambiguous.value.code == "TASK_SKILL_REQUIREMENT_TARGET_AMBIGUOUS"

    with pytest.raises(ValidationError) as exc_mode:
        TaskSkillRequirement.create(
            task_id="task-1",
            skill_code="python",
            validation_mode="manual",
        )
    assert exc_mode.value.code == "TASK_SKILL_REQUIREMENT_MODE_INVALID"


def test_resource_service_skill_and_certification_commands_use_domain_validation() -> None:
    skill_repo = _RecordingSkillRepo()
    cert_repo = _RecordingCertRepo()
    service = _make_resource_service(skill_repo=skill_repo, cert_repo=cert_repo)

    skill = service.add_resource_skill(
        resource_id="  res-1  ",
        skill_code="  PYTHON  ",
        skill_name="  Python  ",
        proficiency="EXPERT",
        notes="  Lead skill  ",
    )
    cert = service.add_resource_certification(
        resource_id="  res-1  ",
        certification_code="  PMP  ",
        certification_name="  PMP  ",
        issued_date=date(2026, 1, 1),
        expiry_date=date(2026, 12, 31),
        issuing_body="  PMI  ",
        notes="  Verified  ",
    )

    assert skill_repo.added[0].skill_code == "python"
    assert skill.proficiency == SkillProficiencyLevel.EXPERT
    assert cert_repo.added[0].certification_code == "pmp"
    assert cert.issuing_body == "PMI"

    with pytest.raises(ValidationError) as exc_skill:
        service.add_resource_skill(
            resource_id="res-1",
            skill_code="python",
            skill_name="Python",
            proficiency="guru",
        )
    assert exc_skill.value.code == "RESOURCE_SKILL_PROFICIENCY_INVALID"

    with pytest.raises(ValidationError) as exc_cert:
        service.add_resource_certification(
            resource_id="res-1",
            certification_code="pmp",
            certification_name="PMP",
            issued_date=date(2026, 12, 31),
            expiry_date=date(2026, 1, 1),
        )
    assert exc_cert.value.code == "RESOURCE_CERTIFICATION_DATE_RANGE_INVALID"
