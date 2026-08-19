"""R4.4G -- movability policy unit tests."""
from __future__ import annotations

from datetime import date

from src.core.modules.project_management.domain.enums import ConstraintType
from src.core.modules.project_management.domain.tasks.task import Task
from src.core.modules.project_management.application.scheduling.leveling.movability_policy import (
    task_movability,
)


def _task(**overrides):
    base = dict(id="a", project_id="p1", name="Task A", duration_days=2, start_date=date(2026, 9, 7))
    base.update(overrides)
    return Task(**base)


def test_asap_task_is_movable_with_no_ceiling():
    decision = task_movability(_task())
    assert decision.movable is True
    assert decision.start_ceiling is None
    assert decision.finish_ceiling is None


def test_snet_task_is_movable():
    decision = task_movability(
        _task(constraint_type=ConstraintType.START_NO_EARLIER_THAN, constraint_date=date(2026, 9, 1))
    )
    assert decision.movable is True


def test_fnet_task_is_movable():
    decision = task_movability(
        _task(constraint_type=ConstraintType.FINISH_NO_EARLIER_THAN, constraint_date=date(2026, 9, 1))
    )
    assert decision.movable is True


def test_snlt_task_is_movable_but_reports_a_start_ceiling():
    decision = task_movability(
        _task(constraint_type=ConstraintType.START_NO_LATER_THAN, constraint_date=date(2026, 9, 20))
    )
    assert decision.movable is True
    assert decision.start_ceiling == date(2026, 9, 20)
    assert decision.finish_ceiling is None


def test_fnlt_task_is_movable_but_reports_a_finish_ceiling():
    decision = task_movability(
        _task(constraint_type=ConstraintType.FINISH_NO_LATER_THAN, constraint_date=date(2026, 9, 20))
    )
    assert decision.movable is True
    assert decision.finish_ceiling == date(2026, 9, 20)


def test_mso_task_is_not_movable():
    decision = task_movability(
        _task(constraint_type=ConstraintType.MUST_START_ON, constraint_date=date(2026, 9, 7))
    )
    assert decision.movable is False
    assert decision.reason == "exact_pin_must_start_on"


def test_mfo_task_is_not_movable():
    decision = task_movability(
        _task(constraint_type=ConstraintType.MUST_FINISH_ON, constraint_date=date(2026, 9, 9))
    )
    assert decision.movable is False
    assert decision.reason == "exact_pin_must_finish_on"


def test_deadline_task_is_movable_and_carries_the_deadline_for_warning_purposes():
    decision = task_movability(_task(deadline=date(2026, 9, 20)))
    assert decision.movable is True
    assert decision.deadline == date(2026, 9, 20)


def test_actual_start_locked_task_is_not_movable():
    decision = task_movability(_task(actual_start=date(2026, 9, 7)))
    assert decision.movable is False
    assert decision.reason == "actual_date_locked"


def test_actual_end_locked_task_is_not_movable():
    decision = task_movability(_task(actual_start=date(2026, 9, 7), actual_end=date(2026, 9, 9)))
    assert decision.movable is False
    assert decision.reason == "actual_date_locked"
