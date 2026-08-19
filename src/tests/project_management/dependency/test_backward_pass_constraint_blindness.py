"""Phase I decision record (R4.4 constraint implementation pass):
backward-pass constraint/float semantics were characterized and
deliberately NOT implemented in this pass. Pinned here as an explicit,
tested decision -- not a silent gap -- so a future R4.4 leveling change
cannot accidentally assume constrained float is authoritative without
someone having to come here and update this test first.

TARGET semantics, reasoned from standard CPM rules (not implemented):

- MUST_START_ON / MUST_FINISH_ON (exact pins): the pinned task's own
  LS/LF should equal its pinned ES/EF -- i.e. zero *own* float, since it
  cannot move regardless of what slack the network would otherwise
  allow. This bound should then propagate backward through predecessors
  exactly like any other successor-derived LS bound already does.
- START_NO_EARLIER_THAN / FINISH_NO_EARLIER_THAN (floors): these already
  raise the forward-pass ES/EF when triggered (see task_date_math.py) --
  once raised, the existing backward-pass math is arguably already
  consistent for them, since LF/LS are derived from the (already-raised)
  network dates. Lower implementation risk than the ceiling/pin cases.
- START_NO_LATER_THAN / FINISH_NO_LATER_THAN (ceilings): should cap the
  task's *effective* LF at the constraint date when the network-implied
  LF exceeds it, which can legitimately drive total float negative
  (revealing an infeasible ceiling) rather than reporting a comfortable
  float number the ceiling actually forbids.
- DEADLINE: same ceiling treatment as FINISH_NO_LATER_THAN, but on
  task.deadline instead of constraint_date.

WHY NOT IMPLEMENTED HERE: run_backward_pass (application/scheduling/
cpm/passes.py) is a single, heavily-depended-on function feeding
float/criticality across the Scheduling workspace, dashboards, and
financial-forecast schedule linkage -- none of which were re-audited in
this pass (explicitly out of scope: "Do NOT re-audit the entire
constraint subsystem"). Changing its output for constrained tasks
without a full regression sweep across all of those consumers is
exactly the "casual rewrite" this directive explicitly warns against.
The six-type persistence/mutation/governance/calendar-policy vertical
slice this pass DID deliver is real and independently valuable; risking
it against an unaudited-blast-radius CPM change was judged the wrong
trade. See R4_4_TASK_CONSTRAINT_IMPLEMENTATION_SUMMARY.md, "Backward
pass decision," for the full writeup.

CONSEQUENCE FOR R4.4: leveling must NOT treat a constrained task's
reported total_float_days/free_float_days/is_critical as authoritative
without accounting for this gap directly (e.g. by consulting
ConstraintValidator's own violation/conflict facts alongside float,
not float alone).
"""
from __future__ import annotations

from datetime import date

from src.core.modules.project_management.domain.enums import ConstraintType
from src.core.modules.project_management.domain.tasks.task import Task
from src.core.modules.project_management.application.scheduling.cpm.pure_cpm import run_cpm


class _MonToFriCalendar:
    def is_working_day(self, target_date: date) -> bool:
        return target_date.weekday() < 5

    def next_working_day(self, target_date: date, include_today: bool = True) -> date:
        current = target_date if include_today else target_date.fromordinal(target_date.toordinal() + 1)
        while not self.is_working_day(current):
            current = current.fromordinal(current.toordinal() + 1)
        return current

    def add_working_days(self, start: date, working_days: int) -> date:
        current = start
        step = 1 if working_days >= 0 else -1
        remaining = abs(working_days)
        while remaining > 0:
            current = current.fromordinal(current.toordinal() + step)
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
            current = current.fromordinal(current.toordinal() + 1)
        return count


def test_a_must_start_on_pinned_task_reports_nonzero_total_float_today():
    """A single, dependency-free task pinned to MUST_START_ON well before
    the (irrelevant, since it has no successors) project finish reports
    float as if the pin didn't exist -- run_backward_pass never reads
    constraint_type/constraint_date. Documents the exact gap described
    above rather than asserting nothing changed."""
    calendar = _MonToFriCalendar()
    task = Task(
        id="pinned",
        project_id="p1",
        name="Pinned Task",
        duration_days=3,
        constraint_type=ConstraintType.MUST_START_ON,
        constraint_date=date(2026, 9, 7),  # a Monday
    )
    result = run_cpm(calendar, {"pinned": task}, [])
    info = result.schedule["pinned"]

    assert info.earliest_start == date(2026, 9, 7)
    # TARGET (per the docstring above): a pinned task's own total float
    # should be 0 -- it cannot move. CURRENT: a lone task with no
    # dependencies is both a root and an end task, so run_backward_pass's
    # own working-day rounding (LS = project_early_finish walked back by
    # duration-1 working days) gives it a nonzero float even though the
    # pin should make it exactly 0 -- observed value pinned here rather
    # than assumed, since the point is documenting real behavior, not a
    # guess. The multi-task case below is the clearer, load-bearing
    # evidence of the actual gap (false float leaking onto A).
    assert info.total_float_days == 1


def test_a_must_start_on_pinned_predecessor_does_not_tighten_a_successors_float():
    """Two tasks, A --FS--> B, A pinned via MUST_START_ON far earlier than
    the network would otherwise place it (there is no earlier bound to
    violate, so the pin simply becomes A's actual date) plus a long gap
    before B's own MUST_START_ON pin much later -- B's own pin means the
    network SHOULD treat both as float-free/critical in a
    constraint-aware backward pass, but since neither pin is read at
    all, B (and therefore A) get whatever float the plain FS
    relationship implies once B's forward-pass MSO override has already
    fired."""
    calendar = _MonToFriCalendar()
    a = Task(
        id="a",
        project_id="p1",
        name="Task A",
        duration_days=2,
        start_date=date(2026, 9, 7),  # Monday
    )
    b = Task(
        id="b",
        project_id="p1",
        name="Task B",
        duration_days=2,
        constraint_type=ConstraintType.MUST_START_ON,
        # Far later than A --FS--> B alone would imply (A finishes
        # 2026-09-08), leaving a large forward-pass gap the backward
        # pass has no way to know is fully consumed by B's own pin.
        constraint_date=date(2026, 9, 21),
    )
    from src.core.modules.project_management.domain.tasks.task import TaskDependency

    dep = TaskDependency.create(a.id, b.id)
    result = run_cpm(calendar, {"a": a, "b": b}, [dep])

    info_a = result.schedule["a"]
    info_b = result.schedule["b"]
    assert info_b.earliest_start == date(2026, 9, 21)  # MSO override confirmed to have fired

    # TARGET: B is pinned -- it cannot move at all, so its own total
    # float should be 0, and A's float should reflect that B (its only
    # successor) has zero slack to offer, not the large FS-implied gap.
    # CURRENT (pinned here): the backward pass computes LF purely from
    # end-task/project_early_finish + dependency propagation, giving B
    # (an end task, since it has no successors) LF == project finish and
    # LS == its own ES -- so B still reports 0 float in this
    # single-chain case too, by construction of it being the LAST task,
    # not because the pin was honored. A, however, DOES show the large
    # false slack: the backward pass lets A's LS drift all the way up to
    # just before B's ACTUAL (pinned) start, reporting float the pin
    # does not actually grant, since nothing tells the backward pass A
    # must still respect its ORIGINAL FS-implied relationship boundary
    # rigidly once B moved.
    assert info_a.total_float_days > 0
