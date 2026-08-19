"""Pure unit tests for the canonical dependency date-math authority.

No DB, no Qt -- fast tests for src/core/.../scheduling/cpm/dependency_schedule_math.py.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from src.core.modules.project_management.domain.enums import DependencyType
from src.core.modules.project_management.application.scheduling.cpm.dependency_schedule_math import (
    UnsupportedDependencyTypeError,
    normalize_forward,
    predecessor_late_boundary,
    shift_working_days,
    successor_boundary,
    successor_earliest_start_from_boundary,
)


class MonToFriCalendar:
    """Weekends-only non-working calendar -- no holidays, matches the
    fixtures used by the existing CPM integration tests."""

    def is_working_day(self, target_date: date) -> bool:
        return target_date.weekday() < 5

    def next_working_day(self, target_date: date, include_today: bool = True) -> date:
        current = target_date if include_today else target_date + timedelta(days=1)
        while not self.is_working_day(current):
            current += timedelta(days=1)
        return current

    def add_working_days(self, start: date, working_days: int) -> date:  # pragma: no cover - unused by this module
        raise NotImplementedError

    def working_days_between(self, start: date, end: date) -> int:  # pragma: no cover - unused by this module
        raise NotImplementedError


@pytest.fixture
def cal() -> MonToFriCalendar:
    return MonToFriCalendar()


# 2026-06-01 is a Monday.
MON, TUE, WED, THU, FRI = (date(2026, 6, 1) + timedelta(days=i) for i in range(5))
NEXT_MON = MON + timedelta(days=7)


def test_shift_zero_is_identity(cal):
    assert shift_working_days(cal, THU, 0) == THU


def test_shift_positive_steps_working_days_only(cal):
    assert shift_working_days(cal, THU, 1) == FRI
    # +2 from Thursday must skip the weekend.
    assert shift_working_days(cal, THU, 2) == NEXT_MON


def test_shift_negative_steps_working_days_only(cal):
    assert shift_working_days(cal, MON, -1) == FRI - timedelta(days=7)
    assert shift_working_days(cal, FRI, -1) == THU


def test_shift_is_strictly_monotonic_for_negative_offsets(cal):
    """The old lag+2/add_working_days formula made FS lag=-1 and lag=-2
    produce the identical date. The canonical primitive must not repeat
    this: every distinct negative offset is a distinct date."""
    anchor = THU
    seen = {shift_working_days(cal, anchor, -n) for n in range(0, 6)}
    assert len(seen) == 6


def test_normalize_forward_rounds_weekend_to_monday(cal):
    saturday = MON - timedelta(days=2)
    assert normalize_forward(cal, saturday) == MON


def test_normalize_forward_is_identity_on_working_day(cal):
    assert normalize_forward(cal, THU) == THU


class TestFinishToStart:
    def test_zero_lag_is_next_working_day_after_finish(self, cal):
        b = successor_boundary(
            cal,
            dependency_type=DependencyType.FINISH_TO_START,
            lag_days=0,
            predecessor_earliest_start=None,
            predecessor_earliest_finish=THU,
        )
        assert b.date == FRI
        assert b.constrains_start is True

    def test_positive_lag_adds_working_days_beyond_the_boundary(self, cal):
        # B2's worked example: pred finishes Thu, FS+1 -> successor starts Mon.
        b = successor_boundary(
            cal,
            dependency_type=DependencyType.FINISH_TO_START,
            lag_days=1,
            predecessor_earliest_start=None,
            predecessor_earliest_finish=THU,
        )
        assert b.date == NEXT_MON

    def test_negative_lead_is_monotonic(self, cal):
        b_minus1 = successor_boundary(
            cal, dependency_type=DependencyType.FINISH_TO_START, lag_days=-1,
            predecessor_earliest_start=None, predecessor_earliest_finish=THU,
        )
        b_minus2 = successor_boundary(
            cal, dependency_type=DependencyType.FINISH_TO_START, lag_days=-2,
            predecessor_earliest_start=None, predecessor_earliest_finish=THU,
        )
        # lag=-1 collapses the +1-working-day buffer: successor may start
        # the SAME day the predecessor finishes.
        assert b_minus1.date == THU
        # lag=-2 must be strictly earlier than lag=-1 -- this is exactly the
        # case the old formula collapsed into a duplicate of lag=-1.
        assert b_minus2.date == WED
        assert b_minus2.date != b_minus1.date


class TestStartToStart:
    def test_zero_lag_allows_same_day_as_predecessor_start(self, cal):
        b = successor_boundary(
            cal, dependency_type=DependencyType.START_TO_START, lag_days=0,
            predecessor_earliest_start=MON, predecessor_earliest_finish=None,
        )
        assert b.date == MON
        assert b.constrains_start is True

    def test_lag_zero_and_lag_one_are_distinguishable(self, cal):
        """Old bug: add_working_days(anchor, 0) == add_working_days(anchor, 1)
        whenever anchor is already a working day, so SS could not tell 0
        from 1 working day of lag. Canonical math must distinguish them."""
        zero = successor_boundary(
            cal, dependency_type=DependencyType.START_TO_START, lag_days=0,
            predecessor_earliest_start=MON, predecessor_earliest_finish=None,
        )
        one = successor_boundary(
            cal, dependency_type=DependencyType.START_TO_START, lag_days=1,
            predecessor_earliest_start=MON, predecessor_earliest_finish=None,
        )
        assert zero.date != one.date
        assert one.date == TUE

    def test_lag_zero_does_not_preserve_a_non_working_anchor(self, cal):
        """Old bug: SS/FF/SF at lag=0 could schedule directly onto a
        non-working day because add_working_days(x, 0) returns x unchanged
        with no working-day check. The canonical anchor must be normalized
        first."""
        saturday = MON - timedelta(days=2)
        b = successor_boundary(
            cal, dependency_type=DependencyType.START_TO_START, lag_days=0,
            predecessor_earliest_start=saturday, predecessor_earliest_finish=None,
        )
        assert b.date == MON
        assert cal.is_working_day(b.date)


class TestFinishToFinish:
    def test_zero_lag_allows_same_day_as_predecessor_finish(self, cal):
        b = successor_boundary(
            cal, dependency_type=DependencyType.FINISH_TO_FINISH, lag_days=0,
            predecessor_earliest_start=None, predecessor_earliest_finish=THU,
        )
        assert b.date == THU
        assert b.constrains_start is False

    def test_back_solve_to_earliest_start(self, cal):
        b = successor_boundary(
            cal, dependency_type=DependencyType.FINISH_TO_FINISH, lag_days=0,
            predecessor_earliest_start=None, predecessor_earliest_finish=THU,
        )
        es = successor_earliest_start_from_boundary(cal, b, successor_duration_days=3)
        # 3-day task finishing Thursday starts Tuesday (Tue, Wed, Thu).
        assert es == THU - timedelta(days=2)


class TestStartToFinish:
    def test_zero_lag_allows_finish_on_predecessor_start_day(self, cal):
        b = successor_boundary(
            cal, dependency_type=DependencyType.START_TO_FINISH, lag_days=0,
            predecessor_earliest_start=MON, predecessor_earliest_finish=None,
        )
        assert b.date == MON
        assert b.constrains_start is False

    def test_ss_and_sf_no_longer_collapse_to_the_same_formula(self, cal):
        """Old bug: for zero-duration tasks, SS and SF computed the
        identical expression add_working_days(pred_es, lag). They must
        remain conceptually distinct (SF constrains finish, not start) even
        though the date happens to coincide for a milestone."""
        ss = successor_boundary(
            cal, dependency_type=DependencyType.START_TO_START, lag_days=2,
            predecessor_earliest_start=MON, predecessor_earliest_finish=None,
        )
        sf = successor_boundary(
            cal, dependency_type=DependencyType.START_TO_FINISH, lag_days=2,
            predecessor_earliest_start=MON, predecessor_earliest_finish=None,
        )
        assert ss.date == sf.date  # same date is fine...
        assert ss.constrains_start is True and sf.constrains_start is False  # ...but not the same meaning


def test_unknown_dependency_type_fails_closed(cal):
    with pytest.raises(UnsupportedDependencyTypeError):
        successor_boundary(
            cal, dependency_type="NOT_A_REAL_TYPE", lag_days=0,
            predecessor_earliest_start=MON, predecessor_earliest_finish=None,
        )


class TestForwardBackwardDuality:
    """The backward pass must be the exact algebraic inverse of the forward
    pass for every type, not just FS -- this is the core Phase C2 fix."""

    @pytest.mark.parametrize(
        "dependency_type",
        [
            DependencyType.FINISH_TO_START,
            DependencyType.START_TO_START,
            DependencyType.FINISH_TO_FINISH,
            DependencyType.START_TO_FINISH,
        ],
    )
    @pytest.mark.parametrize("lag_days", [-3, -1, 0, 1, 2, 5])
    def test_backward_inverts_forward_at_the_exact_boundary(self, cal, dependency_type, lag_days):
        pred_es, pred_ef = MON, WED  # predecessor spans Mon-Wed

        boundary = successor_boundary(
            cal,
            dependency_type=dependency_type,
            lag_days=lag_days,
            predecessor_earliest_start=pred_es,
            predecessor_earliest_finish=pred_ef,
        )

        # Put the successor's own late date exactly on the forward boundary
        # (the tightest possible schedule) and ask the backward formula for
        # the predecessor's latest permissible start. Since duration is
        # collapsed to 1 working day here, "latest start" == the late
        # anchor itself, which must reproduce the same relationship.
        if boundary.constrains_start:
            late = predecessor_late_boundary(
                cal,
                dependency_type=dependency_type,
                lag_days=lag_days,
                successor_latest_start=boundary.date,
                successor_latest_finish=None,
                predecessor_duration_days=1 if _anchors_on_finish(dependency_type) else 0,
            )
        else:
            late = predecessor_late_boundary(
                cal,
                dependency_type=dependency_type,
                lag_days=lag_days,
                successor_latest_start=None,
                successor_latest_finish=boundary.date,
                predecessor_duration_days=1 if _anchors_on_finish(dependency_type) else 0,
            )

        expected_anchor = pred_ef if _anchors_on_finish(dependency_type) else pred_es
        if _anchors_on_finish(dependency_type):
            # predecessor_late_boundary converted an LF bound to an LS bound
            # via a 1-day duration back-solve (LS == LF for duration 1).
            assert late.latest_start == expected_anchor
        else:
            assert late.latest_start == expected_anchor


def _anchors_on_finish(dependency_type: DependencyType) -> bool:
    return dependency_type in (DependencyType.FINISH_TO_START, DependencyType.FINISH_TO_FINISH)
