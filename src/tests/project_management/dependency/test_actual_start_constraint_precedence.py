"""Phase J (R4.4 constraint pass): actuals are historical truth. A
started task's actual_start must not be silently rewritten by a
MUST_START_ON/START_NO_EARLIER_THAN scheduling constraint -- the old
behavior let the constraint unconditionally overwrite it. The fix
preserves the actual date and lets ConstraintValidator report the
resulting mismatch as a real violation, exactly the "task actually
started N working days after its Must Start On constraint" fact the
audit's target behavior calls for.
"""
from __future__ import annotations

from datetime import date, timedelta

from src.core.modules.project_management.application.scheduling.cpm.constraint_validator import (
    ConstraintType,
    ConstraintValidator,
)
from src.core.modules.project_management.application.scheduling.cpm.pure_cpm import run_cpm
from src.core.modules.project_management.domain.tasks.task import Task


class _MonToFriCalendar:
    def is_working_day(self, target_date: date) -> bool:
        return target_date.weekday() < 5

    def next_working_day(self, target_date: date, include_today: bool = True) -> date:
        current = target_date if include_today else target_date + timedelta(days=1)
        while not self.is_working_day(current):
            current += timedelta(days=1)
        return current

    def add_working_days(self, start: date, working_days: int) -> date:
        current = start
        step = 1 if working_days >= 0 else -1
        remaining = abs(working_days)
        while remaining > 0:
            current += timedelta(days=step)
            if self.is_working_day(current):
                remaining -= 1
        return current

    def working_days_between(self, start: date, end: date) -> int:
        if end < start:
            return -self.working_days_between(end, start)
        count = 0
        current = start
        while current <= end:
            if self.is_working_day(current):
                count += 1
            current += timedelta(days=1)
        return count


def test_must_start_on_does_not_overwrite_an_already_started_task():
    calendar = _MonToFriCalendar()
    task = Task(
        id="t1",
        project_id="p1",
        name="Started Task",
        duration_days=3,
        actual_start=date(2026, 9, 10),  # Thursday -- the historical fact
        constraint_type=ConstraintType.MUST_START_ON,
        constraint_date=date(2026, 9, 8),  # Tuesday -- would have overwritten it
    )
    result = run_cpm(calendar, {"t1": task}, [])
    info = result.schedule["t1"]

    # The actual start wins -- not silently rescheduled back to 8 Sep.
    assert info.earliest_start == date(2026, 9, 10)

    # ConstraintValidator reports the mismatch as a real violation,
    # automatically, with no separate variance-tracking code needed --
    # it already compares whatever es/ef ended up being against cd.
    validator = ConstraintValidator(calendar)
    violation_result = validator.validate({"t1": task}, {"t1": info})
    assert not violation_result.is_valid
    violation = violation_result.violations[0]
    assert violation.constraint_type is ConstraintType.MUST_START_ON
    assert violation.computed_date == date(2026, 9, 10)
    assert violation.constraint_date == date(2026, 9, 8)


def test_start_no_earlier_than_does_not_overwrite_an_already_started_task():
    calendar = _MonToFriCalendar()
    task = Task(
        id="t1",
        project_id="p1",
        name="Started Task",
        duration_days=3,
        actual_start=date(2026, 9, 8),  # Tuesday
        constraint_type=ConstraintType.START_NO_EARLIER_THAN,
        constraint_date=date(2026, 9, 15),  # a full week later -- would have floored past the actual
    )
    result = run_cpm(calendar, {"t1": task}, [])
    info = result.schedule["t1"]

    assert info.earliest_start == date(2026, 9, 8)


def test_a_task_with_no_actual_start_is_still_pinned_normally():
    """Regression guard: the fix must not disable MSO for the ordinary,
    not-yet-started case."""
    calendar = _MonToFriCalendar()
    task = Task(
        id="t1",
        project_id="p1",
        name="Not Started Task",
        duration_days=3,
        constraint_type=ConstraintType.MUST_START_ON,
        constraint_date=date(2026, 9, 8),
    )
    result = run_cpm(calendar, {"t1": task}, [])
    assert result.schedule["t1"].earliest_start == date(2026, 9, 8)


def test_must_finish_on_still_sets_finish_but_leaves_a_locked_start_alone():
    calendar = _MonToFriCalendar()
    task = Task(
        id="t1",
        project_id="p1",
        name="Started Task",
        duration_days=3,
        actual_start=date(2026, 9, 8),
        constraint_type=ConstraintType.MUST_FINISH_ON,
        constraint_date=date(2026, 9, 30),
    )
    result = run_cpm(calendar, {"t1": task}, [])
    info = result.schedule["t1"]

    assert info.earliest_start == date(2026, 9, 8)  # untouched
    assert info.earliest_finish == date(2026, 9, 30)  # constraint still honored
