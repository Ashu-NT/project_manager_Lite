"""Server-side enforcement of skill/certification requirements at assignment time."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.core.modules.project_management.application.resources.assignment_validation import (
    AssignmentValidationResult,
    SkillViolation,
)
from src.core.modules.project_management.application.tasks.commands.assignment import (
    TaskAssignmentMixin,
)
from src.core.modules.project_management.domain.resources.skills import SkillValidationMode
from src.core.platform.common.exceptions import BusinessRuleError


class _FakeValidator:
    def __init__(self, result: AssignmentValidationResult) -> None:
        self._result = result
        self.calls: list[tuple[object, str]] = []

    def validate(self, task, resource_id):
        self.calls.append((task, resource_id))
        return self._result


def _make_fake_self(validator) -> SimpleNamespace:
    return SimpleNamespace(
        _assignment_skill_validator=validator,
        _last_skill_violation_warning=None,
    )


def _violation(mode: SkillValidationMode, message: str = "bad") -> SkillViolation:
    return SkillViolation(
        requirement_id="req-1",
        task_id="task-1",
        resource_id="res-1",
        violation_type="missing_skill",
        skill_code="welding",
        certification_code=None,
        required_proficiency=None,
        actual_proficiency=None,
        expiry_date=None,
        message=message,
        validation_mode=mode,
    )


def test_noop_when_no_validator_configured():
    fake_self = _make_fake_self(None)
    task = SimpleNamespace(id="task-1")

    TaskAssignmentMixin._check_resource_skill_requirements(fake_self, task=task, resource_id="res-1")

    assert fake_self._last_skill_violation_warning is None


def test_noop_when_result_has_no_violations():
    result = AssignmentValidationResult(task_id="task-1", resource_id="res-1")
    fake_self = _make_fake_self(_FakeValidator(result))
    task = SimpleNamespace(id="task-1")

    TaskAssignmentMixin._check_resource_skill_requirements(fake_self, task=task, resource_id="res-1")

    assert fake_self._last_skill_violation_warning is None


def test_raises_business_rule_error_when_block_mode_violation_present():
    result = AssignmentValidationResult(
        task_id="task-1",
        resource_id="res-1",
        violations=[_violation(SkillValidationMode.BLOCK, "missing welding cert")],
    )
    fake_self = _make_fake_self(_FakeValidator(result))
    task = SimpleNamespace(id="task-1")

    with pytest.raises(BusinessRuleError) as exc_info:
        TaskAssignmentMixin._check_resource_skill_requirements(fake_self, task=task, resource_id="res-1")

    assert exc_info.value.code == "ASSIGNMENT_SKILL_BLOCKED"
    assert "missing welding cert" in str(exc_info.value)


def test_stashes_warning_when_override_mode_requires_approval():
    result = AssignmentValidationResult(
        task_id="task-1",
        resource_id="res-1",
        violations=[_violation(SkillValidationMode.OVERRIDE, "needs approval override")],
    )
    fake_self = _make_fake_self(_FakeValidator(result))
    task = SimpleNamespace(id="task-1")

    TaskAssignmentMixin._check_resource_skill_requirements(fake_self, task=task, resource_id="res-1")

    assert fake_self._last_skill_violation_warning is not None
    assert "needs approval override" in fake_self._last_skill_violation_warning


def test_stashes_warning_when_warn_mode_violation_present():
    result = AssignmentValidationResult(
        task_id="task-1",
        resource_id="res-1",
        warnings=[_violation(SkillValidationMode.WARN, "soft skill gap")],
    )
    fake_self = _make_fake_self(_FakeValidator(result))
    task = SimpleNamespace(id="task-1")

    TaskAssignmentMixin._check_resource_skill_requirements(fake_self, task=task, resource_id="res-1")

    assert fake_self._last_skill_violation_warning is not None
    assert "soft skill gap" in fake_self._last_skill_violation_warning


def test_validator_called_with_task_and_resource_id():
    result = AssignmentValidationResult(task_id="task-1", resource_id="res-1")
    validator = _FakeValidator(result)
    fake_self = _make_fake_self(validator)
    task = SimpleNamespace(id="task-1")

    TaskAssignmentMixin._check_resource_skill_requirements(fake_self, task=task, resource_id="res-1")

    assert validator.calls == [(task, "res-1")]
