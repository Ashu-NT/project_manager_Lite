"""Unit tests for ConstraintValidator — pure domain logic, no DB or Qt."""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.core.modules.project_management.application.scheduling.cpm.constraint_validator import (
    ConstraintType,
    ConstraintValidator,
)
from src.core.modules.project_management.application.scheduling.models.cpm import CPMTaskInfo
from src.core.modules.project_management.domain.tasks.task import Task
from src.core.platform.common.exceptions import ValidationError


def _task(constraint_type=None, constraint_date=None, deadline=None, **kwargs) -> Task:

    return Task(
        id="t1",
        project_id="p1",
        name="Test Task",
        duration_days=5,
        constraint_type=constraint_type,
        constraint_date=constraint_date,
        deadline=deadline,
        **kwargs,
    )


def _info(es: date, ef: date, *, dependency_implied_start=None, dependency_implied_finish=None) -> CPMTaskInfo:
    m = MagicMock(spec=CPMTaskInfo)
    m.earliest_start = es
    m.earliest_finish = ef
    # MagicMock(spec=...) does not honor dataclass field defaults --
    # dependency_implied_start/finish must be explicitly set to None,
    # otherwise accessing them returns a truthy child mock and
    # ConstraintValidator._check_dependency_conflict (Phase F) would treat
    # that as a real implied date.
    m.dependency_implied_start = dependency_implied_start
    m.dependency_implied_finish = dependency_implied_finish
    return m


def _calendar():
    cal = MagicMock()
    cal.working_days_between = lambda s, e: max(0, (e - s).days)
    return cal


@pytest.fixture
def validator():
    return ConstraintValidator(calendar=_calendar())


class TestMustStartOn:
    def test_pass_when_matches(self, validator):
        t = _task(constraint_type=ConstraintType.MUST_START_ON, constraint_date=date(2026, 6, 1))
        result = validator.validate({"t1": t}, {"t1": _info(date(2026, 6, 1), date(2026, 6, 6))})
        assert result.is_valid

    def test_fail_when_es_differs(self, validator):
        t = _task(constraint_type=ConstraintType.MUST_START_ON, constraint_date=date(2026, 6, 1))
        result = validator.validate({"t1": t}, {"t1": _info(date(2026, 6, 3), date(2026, 6, 8))})
        assert not result.is_valid
        assert result.hard_violations[0].constraint_type == ConstraintType.MUST_START_ON


class TestMustFinishOn:
    def test_fail_when_ef_differs(self, validator):
        t = _task(constraint_type=ConstraintType.MUST_FINISH_ON, constraint_date=date(2026, 6, 10))
        result = validator.validate({"t1": t}, {"t1": _info(date(2026, 6, 3), date(2026, 6, 8))})
        assert not result.is_valid
        assert result.hard_violations[0].constraint_type == ConstraintType.MUST_FINISH_ON


class TestStartNoLaterThan:
    def test_pass_when_on_time(self, validator):
        t = _task(constraint_type=ConstraintType.START_NO_LATER_THAN, constraint_date=date(2026, 6, 5))
        result = validator.validate({"t1": t}, {"t1": _info(date(2026, 6, 3), date(2026, 6, 8))})
        assert result.is_valid

    def test_fail_when_late(self, validator):
        t = _task(constraint_type=ConstraintType.START_NO_LATER_THAN, constraint_date=date(2026, 6, 2))
        result = validator.validate({"t1": t}, {"t1": _info(date(2026, 6, 5), date(2026, 6, 10))})
        assert not result.is_valid
        assert result.hard_violations[0].constraint_type == ConstraintType.START_NO_LATER_THAN


class TestDeadline:
    def test_fail_when_ef_exceeds_deadline(self, validator):
        t = _task(deadline=date(2026, 6, 5))
        result = validator.validate({"t1": t}, {"t1": _info(date(2026, 6, 1), date(2026, 6, 10))})
        assert not result.is_valid
        assert result.hard_violations[0].constraint_type == ConstraintType.DEADLINE

    def test_pass_when_ef_on_deadline(self, validator):
        t = _task(deadline=date(2026, 6, 10))
        result = validator.validate({"t1": t}, {"t1": _info(date(2026, 6, 1), date(2026, 6, 10))})
        assert result.is_valid


class TestSoftViolations:
    def test_snet_soft_when_too_early(self, validator):
        t = _task(
            constraint_type=ConstraintType.START_NO_EARLIER_THAN,
            constraint_date=date(2026, 6, 10),
        )
        result = validator.validate({"t1": t}, {"t1": _info(date(2026, 6, 5), date(2026, 6, 10))})
        assert not result.is_valid
        assert result.soft_violations[0].constraint_type == ConstraintType.START_NO_EARLIER_THAN
        assert result.hard_violations == []

    def test_fnet_soft_when_too_early(self, validator):
        t = _task(
            constraint_type=ConstraintType.FINISH_NO_EARLIER_THAN,
            constraint_date=date(2026, 6, 20),
        )
        result = validator.validate({"t1": t}, {"t1": _info(date(2026, 6, 10), date(2026, 6, 15))})
        assert not result.is_valid
        assert result.soft_violations[0].constraint_type == ConstraintType.FINISH_NO_EARLIER_THAN


class TestNoConstraint:
    def test_no_violations_when_no_constraint(self, validator):
        t = _task()
        result = validator.validate({"t1": t}, {"t1": _info(date(2026, 6, 1), date(2026, 6, 6))})
        assert result.is_valid

    def test_unknown_constraint_type_string_fails_closed_at_the_domain_boundary(self):
        """R4.4 hardening: a real Task can no longer be constructed with an
        invalid constraint_type -- it must fail closed, not be silently
        treated as unset (the old, now-obsolete behavior this test used to
        assert)."""
        with pytest.raises(ValidationError) as exc_info:
            Task(
                id="t1",
                project_id="p1",
                name="Test Task",
                duration_days=5,
                constraint_type="unknown_type_xyz",
                constraint_date=date(2026, 6, 1),
            )
        assert exc_info.value.code == "TASK_CONSTRAINT_TYPE_INVALID"

    def test_validator_defensively_ignores_an_invalid_duck_typed_constraint_type(self, validator):
        """ConstraintValidator's duck-typed reader is a defensive fallback
        for legacy/corrupt data that bypassed domain validation (e.g. a
        raw object, not a real Task) -- it must not crash, and must treat
        an unrecognized value as no constraint."""
        t = SimpleNamespace(
            constraint_type="unknown_type_xyz",
            constraint_date=date(2026, 6, 1),
            deadline=None,
            id="t1",
            name="Legacy Task",
        )
        result = validator.validate({"t1": t}, {"t1": _info(date(2026, 6, 5), date(2026, 6, 10))})
        assert result.is_valid
