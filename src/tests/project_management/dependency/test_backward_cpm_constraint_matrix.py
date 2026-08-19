"""SNET/FNET floors, Deadline-vs-FNLT distinction, all four dependency types combined with a
constraint, multiple predecessors, actual-date handling, a
non-weekend-only calendar, and free-float behavior on constrained tasks.

"""
from __future__ import annotations

from datetime import date, timedelta

from src.core.modules.project_management.domain.enums import ConstraintType, DependencyType
from src.core.modules.project_management.domain.tasks.task import Task, TaskDependency
from src.core.modules.project_management.application.scheduling.cpm.pure_cpm import run_cpm
from src.core.modules.project_management.application.scheduling.forecasting.task_schedule_overview import (
    compute_free_float_days,
)


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
            return 0
        count = 0
        current = start
        while current <= end:
            if self.is_working_day(current):
                count += 1
            current += timedelta(days=1)
        return count


class _CalendarWithHoliday(_MonToFriCalendar):
    """Mon-Fri PLUS one explicit mid-week holiday, so calendar-sensitive
    tests are not accidentally passing only because every non-working
    day happens to be a weekend -- proves the constraint adjustment
    routes every date shift through the SAME injected CalendarProtocol,
    not a hardcoded Mon-Fri assumption (directive item 12)."""

    def __init__(self, holidays: set[date]) -> None:
        self._holidays = holidays

    def is_working_day(self, target_date: date) -> bool:
        return super().is_working_day(target_date) and target_date not in self._holidays


def _fs(pred: Task, succ: Task, lag_days: int = 0) -> TaskDependency:
    return TaskDependency.create(pred.id, succ.id, DependencyType.FINISH_TO_START, lag_days=lag_days)


# ── 1. Unconstrained baseline (regression) ─────────────────────────────


class TestUnconstrainedBaselineUnchanged:
    """Values here are verified, BEFORE this pass's changes too (by
    diffing against the stashed pre-fix code), to be byte-identical --
    they pin down the codebase's existing end-task backward-pass
    arithmetic (LS derived from the project finish via
    ``add_working_days(pef, -(duration-1))``), which has an established,
    PRE-EXISTING off-by-one quality relative to a naive "solo task has
    zero float" expectation and is out of this pass's scope to change
    (directive item 2: preserve current, unconstrained behavior
    unchanged). The point of these tests is only to prove that claim
    with real numbers, not to assert an idealized value."""

    def test_single_task_no_constraint(self):
        calendar = _MonToFriCalendar()
        task = Task(id="a", project_id="p1", name="Task A", duration_days=3, start_date=date(2026, 9, 7))
        result = run_cpm(calendar, {"a": task}, [])
        info = result.schedule["a"]

        assert info.earliest_start == date(2026, 9, 7)
        assert info.earliest_finish == date(2026, 9, 10)
        assert info.latest_start == date(2026, 9, 8)
        assert info.latest_finish == date(2026, 9, 10)
        assert info.total_float_days == 1
        assert info.is_critical is False
        assert info.is_infeasible is False

    def test_chain_with_dependency_no_constraint(self):
        calendar = _MonToFriCalendar()
        a = Task(id="a", project_id="p1", name="Task A", duration_days=2, start_date=date(2026, 9, 7))
        b = Task(id="b", project_id="p1", name="Task B", duration_days=2)
        result = run_cpm(calendar, {"a": a, "b": b}, [_fs(a, b)])
        info_a = result.schedule["a"]
        info_b = result.schedule["b"]

        assert info_a.total_float_days == 2
        assert info_b.total_float_days == 1
        assert info_a.is_infeasible is False
        assert info_b.is_infeasible is False


# ── 2. SNET / FNET floors -- no backward-pass change expected ──────────


class TestFloorsAlreadyConsistent:
    def test_snet_floor_not_triggered_backward_pass_unaffected(self):
        calendar = _MonToFriCalendar()
        a = Task(id="a", project_id="p1", name="Task A", duration_days=2, start_date=date(2026, 9, 7))
        b = Task(
            id="b", project_id="p1", name="Task B", duration_days=2,
            constraint_type=ConstraintType.START_NO_EARLIER_THAN,
            constraint_date=date(2026, 9, 1),  # already satisfied by the dependency
        )
        result = run_cpm(calendar, {"a": a, "b": b}, [_fs(a, b)])
        info_b = result.schedule["b"]

        assert info_b.earliest_start == date(2026, 9, 10)  # dependency-derived, floor not binding
        # Identical to the no-constraint baseline's B (TestUnconstrained
        # BaselineUnchanged) -- proves a non-binding SNET floor changes
        # nothing about the backward pass, exactly as designed.
        assert info_b.total_float_days == 1
        assert info_b.is_infeasible is False

    def test_snet_floor_triggered_raises_est_and_stays_noncritical(self):
        calendar = _MonToFriCalendar()
        a = Task(id="a", project_id="p1", name="Task A", duration_days=1, start_date=date(2026, 9, 7))
        b = Task(
            id="b", project_id="p1", name="Task B", duration_days=2,
            constraint_type=ConstraintType.START_NO_EARLIER_THAN,
            constraint_date=date(2026, 9, 21),  # well past the dependency-implied start
        )
        result = run_cpm(calendar, {"a": a, "b": b}, [_fs(a, b)])
        info_b = result.schedule["b"]

        assert info_b.earliest_start == date(2026, 9, 21)  # floor raised est
        # Same pre-existing end-task quirk as the baseline (float=1, not
        # 0) -- SNET needs no backward-pass adjustment of its own; the
        # forward-raised est/eft alone already flow through correctly.
        assert info_b.total_float_days == 1
        assert info_b.is_infeasible is False

    def test_fnet_floor_triggered_raises_eft(self):
        calendar = _MonToFriCalendar()
        task = Task(
            id="a", project_id="p1", name="Task A", duration_days=2, start_date=date(2026, 9, 7),
            constraint_type=ConstraintType.FINISH_NO_EARLIER_THAN,
            constraint_date=date(2026, 9, 21),
        )
        result = run_cpm(calendar, {"a": task}, [])
        info = result.schedule["a"]

        assert info.earliest_finish == date(2026, 9, 21)
        assert info.total_float_days == 0
        assert info.is_infeasible is False


# ── 3. Deadline: separate ceiling, never becomes FNLT ──────────────────


class TestDeadlineDistinctFromFnlt:
    def test_deadline_within_bound_is_feasible(self):
        calendar = _MonToFriCalendar()
        task = Task(
            id="a", project_id="p1", name="Task A", duration_days=2, start_date=date(2026, 9, 7),
            deadline=date(2026, 9, 30),
        )
        result = run_cpm(calendar, {"a": task}, [])
        info = result.schedule["a"]

        assert info.is_infeasible is False
        assert info.late_by_days is None

    def test_deadline_exceeded_reports_negative_float_and_late_by_days(self):
        calendar = _MonToFriCalendar()
        a = Task(id="a", project_id="p1", name="Task A", duration_days=3, start_date=date(2026, 9, 7))
        b = Task(
            id="b", project_id="p1", name="Task B", duration_days=2,
            deadline=date(2026, 9, 8),  # earlier than the dependency-implied start
        )
        result = run_cpm(calendar, {"a": a, "b": b}, [_fs(a, b)])
        info_b = result.schedule["b"]

        assert info_b.earliest_start == date(2026, 9, 11)
        assert info_b.total_float_days is not None and info_b.total_float_days < 0
        assert info_b.is_infeasible is True
        assert info_b.late_by_days is not None and info_b.late_by_days > 0

    def test_deadline_never_reported_as_fnlt_constraint_type(self):
        """A task with ONLY task.deadline set (no constraint_type) must
        never have its own constraint_type field coerced into FNLT --
        Deadline and FINISH_NO_LATER_THAN stay separate facts even
        though they receive the same backward-pass ceiling treatment."""
        calendar = _MonToFriCalendar()
        task = Task(
            id="a", project_id="p1", name="Task A", duration_days=2, start_date=date(2026, 9, 7),
            deadline=date(2026, 9, 8),
        )
        result = run_cpm(calendar, {"a": task}, [])
        info = result.schedule["a"]

        assert info.task.constraint_type is None
        assert info.deadline == date(2026, 9, 8)
        assert info.is_infeasible is True


# ── 4. All four dependency types combined with a ceiling constraint ────


class TestDependencyTypesWithConstraint:
    def test_ss_dependency_with_successor_snlt_ceiling(self):
        calendar = _MonToFriCalendar()
        a = Task(id="a", project_id="p1", name="Task A", duration_days=3, start_date=date(2026, 9, 7))
        b = Task(
            id="b", project_id="p1", name="Task B", duration_days=2,
            constraint_type=ConstraintType.START_NO_LATER_THAN,
            constraint_date=date(2026, 9, 8),  # earlier than the SS-implied start
        )
        dep = TaskDependency.create(a.id, b.id, DependencyType.START_TO_START, lag_days=0)
        result = run_cpm(calendar, {"a": a, "b": b}, [dep])
        info_b = result.schedule["b"]

        assert info_b.earliest_start == date(2026, 9, 7)  # SS: same day as A's start
        assert info_b.is_infeasible is False  # SNLT (Sep 8) not violated by Sep 7

    def test_ff_dependency_with_successor_mfo_pin(self):
        calendar = _MonToFriCalendar()
        a = Task(id="a", project_id="p1", name="Task A", duration_days=3, start_date=date(2026, 9, 7))
        b = Task(
            id="b", project_id="p1", name="Task B", duration_days=2,
            constraint_type=ConstraintType.MUST_FINISH_ON,
            constraint_date=date(2026, 9, 8),  # earlier than the FF-implied finish
        )
        dep = TaskDependency.create(a.id, b.id, DependencyType.FINISH_TO_FINISH, lag_days=0)
        result = run_cpm(calendar, {"a": a, "b": b}, [dep])
        info_b = result.schedule["b"]

        # MFO always wins in the forward pass -- the pin fixes the finish
        # regardless of what the FF relationship alone would imply.
        assert info_b.earliest_finish == date(2026, 9, 8)
        assert info_b.total_float_days == 0
        assert info_b.is_critical is True

    def test_sf_dependency_with_successor_fnlt_ceiling(self):
        calendar = _MonToFriCalendar()
        a = Task(id="a", project_id="p1", name="Task A", duration_days=3, start_date=date(2026, 9, 7))
        b = Task(
            id="b", project_id="p1", name="Task B", duration_days=2,
            constraint_type=ConstraintType.FINISH_NO_LATER_THAN,
            constraint_date=date(2026, 9, 8),
        )
        dep = TaskDependency.create(a.id, b.id, DependencyType.START_TO_FINISH, lag_days=0)
        result = run_cpm(calendar, {"a": a, "b": b}, [dep])
        info_b = result.schedule["b"]

        # SF: B's finish is anchored to A's START (Sep 7), well within the
        # Sep 8 ceiling -- feasible, not infeasible.
        assert info_b.is_infeasible is False

    def test_fs_dependency_with_successor_snlt_infeasible(self):
        """FS case duplicated here alongside its SS/FF/SF siblings so the
        matrix is visibly complete for all four types, not just spread
        across other files."""
        calendar = _MonToFriCalendar()
        a = Task(id="a", project_id="p1", name="Task A", duration_days=3, start_date=date(2026, 9, 7))
        b = Task(
            id="b", project_id="p1", name="Task B", duration_days=2,
            constraint_type=ConstraintType.START_NO_LATER_THAN,
            constraint_date=date(2026, 9, 8),
        )
        result = run_cpm(calendar, {"a": a, "b": b}, [_fs(a, b)])
        info_b = result.schedule["b"]

        assert info_b.is_infeasible is True


# ── 5. Multiple predecessors + a constraint on the shared successor ───


class TestMultiplePredecessorsWithConstraint:
    def test_max_of_three_predecessor_types_plus_snlt_ceiling(self):
        """A --FS--> D, B --SS--> D, C --FF--> D, D has an SNLT ceiling
        earlier than what the predecessor max() requires -- forward
        boundary must still be the max of the three; the ceiling must
        still surface as infeasible on top of that max, not silently
        replace it."""
        calendar = _MonToFriCalendar()
        a = Task(id="a", project_id="p1", name="Task A", duration_days=2, start_date=date(2026, 9, 7))
        b = Task(id="b", project_id="p1", name="Task B", duration_days=1, start_date=date(2026, 9, 9))
        c = Task(id="c", project_id="p1", name="Task C", duration_days=4, start_date=date(2026, 9, 7))
        d = Task(
            id="d", project_id="p1", name="Task D", duration_days=2,
            constraint_type=ConstraintType.START_NO_LATER_THAN,
            constraint_date=date(2026, 9, 8),
        )
        deps = [
            _fs(a, d),
            TaskDependency.create(b.id, d.id, DependencyType.START_TO_START, lag_days=0),
            TaskDependency.create(c.id, d.id, DependencyType.FINISH_TO_FINISH, lag_days=0),
        ]
        result = run_cpm(calendar, {"a": a, "b": b, "c": c, "d": d}, deps)
        info_d = result.schedule["d"]

        # Whatever the max()-derived earliest_start actually is, it must
        # be later than the Sep 8 ceiling for this fixture to be a
        # meaningful infeasibility check.
        assert info_d.earliest_start is not None and info_d.earliest_start > date(2026, 9, 8)
        assert info_d.is_infeasible is True
        assert info_d.latest_start == date(2026, 9, 8)


# ── 6. Actual dates ─────────────────────────────────────────────────────


class TestActualDates:
    def test_completed_task_ignores_ceiling_entirely(self):
        """actual_end set -- historical fact, not subject to any further
        constraint/ceiling adjustment even if one is present."""
        calendar = _MonToFriCalendar()
        task = Task(
            id="a", project_id="p1", name="Task A", duration_days=2,
            actual_start=date(2026, 9, 7), actual_end=date(2026, 9, 9),
            constraint_type=ConstraintType.FINISH_NO_LATER_THAN,
            constraint_date=date(2026, 9, 8),  # would otherwise be violated
        )
        result = run_cpm(calendar, {"a": task}, [])
        info = result.schedule["a"]

        assert info.earliest_start == date(2026, 9, 7)
        assert info.earliest_finish == date(2026, 9, 9)
        assert info.latest_start == date(2026, 9, 7)
        assert info.latest_finish == date(2026, 9, 9)
        assert info.total_float_days == 0
        assert info.is_infeasible is False  # historical fact, not a violation to surface here

    def test_started_but_unfinished_task_start_does_not_move(self):
        """actual_start set, no actual_end -- the start dimension must
        stay pinned to history (own start float 0) while the finish
        dimension is still capped by a FINISH_NO_LATER_THAN ceiling that
        the actual-implied finish (2026-09-10, three working days from
        the actual start) already exceeds.

        is_infeasible/total_float_days stay ES/LS-based (this codebase's
        one existing float metric, per results.py) and so do NOT flip
        for this case: ES and LS are both 2026-09-07, giving ordinary
        zero float on the START dimension, which is honestly what "the
        start already happened and cannot move" means. The genuine
        FINISH-side infeasibility (earliest_finish 2026-09-10 exceeds
        the 2026-09-08 ceiling) is a real violation, but it is a
        different fact -- it is what ConstraintValidator's own
        ConstraintViolation already exists to report, independent of
        this pass's ES/LS-based is_infeasible flag. Deliberately not
        widening is_infeasible into a second, finish-based float metric
        here -- see R4_4_TASK_CONSTRAINT_IMPLEMENTATION_SUMMARY.md's
        "Constraint-aware backward CPM" section for the explicit scope
        boundary."""
        calendar = _MonToFriCalendar()
        task = Task(
            id="a", project_id="p1", name="Task A", duration_days=3,
            actual_start=date(2026, 9, 7),
            constraint_type=ConstraintType.FINISH_NO_LATER_THAN,
            constraint_date=date(2026, 9, 8),  # tighter than the actual-implied finish
        )
        result = run_cpm(calendar, {"a": task}, [])
        info = result.schedule["a"]

        assert info.earliest_start == date(2026, 9, 7)
        assert info.earliest_finish == date(2026, 9, 10)
        assert info.latest_start == date(2026, 9, 7)  # pinned to actual_start, unmoved
        assert info.latest_finish == date(2026, 9, 8)  # capped by the ceiling
        assert info.total_float_days == 0  # ES/LS-based metric: start dimension is exactly tight
        assert info.is_infeasible is False

        from src.core.modules.project_management.application.scheduling.cpm.constraint_validator import (
            ConstraintValidator,
        )

        violations = ConstraintValidator(calendar).validate({"a": task}, result.schedule).violations
        assert any(v.constraint_type == ConstraintType.FINISH_NO_LATER_THAN for v in violations)


# ── 7. Calendar: a non-weekend-only holiday must be honored ────────────


class TestCalendarAuthority:
    def test_backward_shift_skips_an_explicit_mid_week_holiday(self):
        """2026-09-09 (a Wednesday) is an explicit holiday on top of the
        normal weekend closures -- every date shift the constraint
        adjustment performs must route through the SAME injected
        calendar, so the holiday is honored identically to the forward
        pass's own shifts."""
        holiday = date(2026, 9, 9)
        calendar = _CalendarWithHoliday({holiday})
        a = Task(id="a", project_id="p1", name="Task A", duration_days=1, start_date=date(2026, 9, 7))
        b = Task(
            id="b", project_id="p1", name="Task B", duration_days=2,
            constraint_type=ConstraintType.START_NO_LATER_THAN,
            constraint_date=date(2026, 9, 10),
        )
        result = run_cpm(calendar, {"a": a, "b": b}, [_fs(a, b)])
        info_b = result.schedule["b"]

        assert info_b.earliest_start == date(2026, 9, 8)  # A finishes Sep7, B starts next working day
        # Latest finish derived from latest_start via shift_working_days,
        # skipping the Sep 9 holiday: Sep10 -> +1 working day -> Sep11
        # (Sep 9 is closed, so the next working day after Sep 10 is
        # Sep 11, not Sep 9).
        assert info_b.latest_start == date(2026, 9, 10)
        assert info_b.latest_finish == date(2026, 9, 11)
        assert holiday not in (info_b.latest_start, info_b.latest_finish)


# ── 8. Free float on constrained tasks (audit -- no code change needed) ─


class TestFreeFloatOnConstrainedTasks:
    """compute_free_float_days (task_schedule_overview.py) is audited,
    not modified, by this pass: it is computed purely from EARLIEST
    dates (a task's own ES/EF vs. its successors' ES), never from
    LS/LF -- so it was already correct wherever a constraint's effect
    flows through the (unchanged) forward pass, and it is unaffected by
    this pass's backward-pass changes EXCEPT for its own documented
    fallback (a leaf task with no successors reports its
    total_float_days as its free float), which now correctly inherits
    the fixed, possibly-negative total_float_days value."""

    def test_leaf_pinned_task_free_float_equals_zero(self):
        calendar = _MonToFriCalendar()
        task = Task(
            id="a", project_id="p1", name="Task A", duration_days=3,
            constraint_type=ConstraintType.MUST_START_ON,
            constraint_date=date(2026, 9, 7),
        )
        result = run_cpm(calendar, {"a": task}, [])
        free_float = compute_free_float_days("a", result.schedule, [], calendar)

        assert free_float == 0

    def test_leaf_infeasible_ceiling_task_free_float_is_negative(self):
        calendar = _MonToFriCalendar()
        a = Task(id="a", project_id="p1", name="Task A", duration_days=3, start_date=date(2026, 9, 7))
        b = Task(
            id="b", project_id="p1", name="Task B", duration_days=2,
            constraint_type=ConstraintType.START_NO_LATER_THAN,
            constraint_date=date(2026, 9, 8),
        )
        dep = _fs(a, b)
        result = run_cpm(calendar, {"a": a, "b": b}, [dep])
        free_float = compute_free_float_days("b", result.schedule, [dep], calendar)

        # B has no successors of its own -- free float falls back to its
        # (now correctly negative) total float.
        assert free_float == result.schedule["b"].total_float_days
        assert free_float is not None and free_float < 0
