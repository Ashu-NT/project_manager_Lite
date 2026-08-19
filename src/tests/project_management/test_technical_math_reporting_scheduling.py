from datetime import date

import pytest

from src.core.modules.project_management.domain.enums import CostType, DependencyType, TaskStatus


def _bar_map(bars):
    return {b.task_id: b for b in bars}


def _row_sum(rows, key_text: str, field: str) -> float:
    total = 0.0
    for r in rows:
        if key_text in str(r.cost_type):
            total += float(getattr(r, field, 0.0) or 0.0)
    return total


def test_cpm_dependency_type_math(services):
    ps = services["project_service"]
    ts = services["task_service"]
    wc = services["work_calendar_engine"]
    sched = services["scheduling_engine"]

    project = ps.create_project("CPM Math", "")
    pid = project.id

    pred = ts.create_task(pid, "Pred", start_date=date(2023, 11, 6), duration_days=3)
    fs = ts.create_task(pid, "TaskFS", duration_days=2)
    ss = ts.create_task(pid, "TaskSS", duration_days=2)
    ff = ts.create_task(pid, "TaskFF", duration_days=2)
    sf = ts.create_task(pid, "TaskSF", duration_days=2)

    ts.add_dependency(pred.id, fs.id, DependencyType.FINISH_TO_START, lag_days=2)
    ts.add_dependency(pred.id, ss.id, DependencyType.START_TO_START, lag_days=3)
    ts.add_dependency(pred.id, ff.id, DependencyType.FINISH_TO_FINISH, lag_days=2)
    ts.add_dependency(pred.id, sf.id, DependencyType.START_TO_FINISH, lag_days=3)

    result = sched.recalculate_project_schedule(pid)
    p = result[pred.id]

    fs_info = result[fs.id]
    # FS starts on next working day after predecessor finish, then applies lag days.
    fs_base_start = wc.next_working_day(p.earliest_finish, include_today=False)
    exp_fs_start = wc.add_working_days(fs_base_start, 3)
    exp_fs_finish = wc.add_working_days(exp_fs_start, 2)
    assert fs_info.earliest_start == exp_fs_start
    assert fs_info.earliest_finish == exp_fs_finish

    # SS/FF/SF zero-lag boundary is "same day as the anchor" (not "next
    # working day after", unlike FS), so N days of lag beyond that boundary
    # is add_working_days(anchor, N + 1) -- the same "+1" trick used for FS
    # above, just without FS's extra zero-lag offset. See
    # docs/pm_modernization/R4_4_TASK_DEPENDENCY_CURRENT_STATE_AND_TARGET_GAPS.md
    # §5/§11/Phase B for why bare `add_working_days(anchor, lag)` (the
    # pre-fix formula this test used to assert) was wrong: it gave SS/FF/SF
    # one fewer working day of separation than FS for the "same" lag value,
    # and could not tell lag=0 apart from lag=1.
    ss_info = result[ss.id]
    exp_ss_start = wc.add_working_days(p.earliest_start, 3 + 1)
    exp_ss_finish = wc.add_working_days(exp_ss_start, 2)
    assert ss_info.earliest_start == exp_ss_start
    assert ss_info.earliest_finish == exp_ss_finish

    ff_info = result[ff.id]
    exp_ff_finish = wc.add_working_days(p.earliest_finish, 2 + 1)
    exp_ff_start = wc.add_working_days(exp_ff_finish, -1)
    assert ff_info.earliest_start == exp_ff_start
    assert ff_info.earliest_finish == exp_ff_finish

    sf_info = result[sf.id]
    sf_target_finish = wc.add_working_days(p.earliest_start, 3 + 1)
    exp_sf_start = wc.add_working_days(sf_target_finish, -1)
    exp_sf_finish = wc.add_working_days(exp_sf_start, 2)
    assert sf_info.earliest_start == exp_sf_start
    assert sf_info.earliest_finish == exp_sf_finish


def test_ss_lag_zero_and_lag_one_are_now_distinguishable(services):
    """Regression for the exact bug flagged in the R4.4 dependency audit:
    under the old add_working_days(anchor, lag) formula, SS/FF/SF lag=0 and
    lag=1 produced the identical date whenever the predecessor's anchor date
    already fell on a working day. The canonical dependency math must
    distinguish them."""
    ps = services["project_service"]
    ts = services["task_service"]
    sched = services["scheduling_engine"]

    project = ps.create_project("SS Lag Zero Vs One", "")
    pid = project.id

    pred = ts.create_task(pid, "Pred", start_date=date(2023, 11, 6), duration_days=1)
    ss_lag0 = ts.create_task(pid, "SS Lag0", duration_days=1)
    ss_lag1 = ts.create_task(pid, "SS Lag1", duration_days=1)

    ts.add_dependency(pred.id, ss_lag0.id, DependencyType.START_TO_START, lag_days=0)
    ts.add_dependency(pred.id, ss_lag1.id, DependencyType.START_TO_START, lag_days=1)

    result = sched.recalculate_project_schedule(pid)

    assert result[ss_lag0.id].earliest_start == pred.start_date
    assert result[ss_lag1.id].earliest_start != result[ss_lag0.id].earliest_start


def test_fs_negative_lead_is_monotonic(services):
    """Regression for the audit's negative-lag finding: FS lag=-1 and
    lag=-2 must not collapse to the same date."""
    ps = services["project_service"]
    ts = services["task_service"]
    sched = services["scheduling_engine"]

    project = ps.create_project("FS Negative Lead", "")
    pid = project.id

    pred = ts.create_task(pid, "Pred", start_date=date(2023, 11, 6), duration_days=3)
    succ_lead1 = ts.create_task(pid, "Lead1", duration_days=1)
    succ_lead2 = ts.create_task(pid, "Lead2", duration_days=1)

    ts.add_dependency(pred.id, succ_lead1.id, DependencyType.FINISH_TO_START, lag_days=-1)
    ts.add_dependency(pred.id, succ_lead2.id, DependencyType.FINISH_TO_START, lag_days=-2)

    result = sched.recalculate_project_schedule(pid)

    # lag=-1 collapses FS's +1-working-day buffer: successor may start the
    # same day the predecessor finishes.
    assert result[succ_lead1.id].earliest_start == result[pred.id].earliest_finish
    # lag=-2 must be strictly earlier than lag=-1.
    assert result[succ_lead2.id].earliest_start < result[succ_lead1.id].earliest_start


def test_mixed_successor_types_both_constrain_predecessor_late_dates(services):
    """Regression for the audit's backward-pass shadowing bug
    (docs/pm_modernization/R4_4_TASK_DEPENDENCY_CURRENT_STATE_AND_TARGET_GAPS.md
    §11): the old code took the FS/FF-derived late-finish candidates
    (`cand_lf_dates`) whenever ANY existed, discarding the SS/SF-derived
    late-start candidates (`cand_ls_dates`) entirely on that predecessor,
    even when the SS/SF bound was the tighter (more constraining) one.

    Construct exactly that case: an FS successor with a short duration (so
    its own latest-start sits right at the project's late finish) and an SS
    successor with a much longer duration (so its own latest-start is
    pulled far earlier). The predecessor's latest start must reflect the
    tighter SS-derived bound, not just the looser FS-derived one.
    """
    ps = services["project_service"]
    ts = services["task_service"]
    sched = services["scheduling_engine"]

    project = ps.create_project("Mixed Successor Types", "")
    pid = project.id

    pred = ts.create_task(pid, "Pred", start_date=date(2023, 11, 6), duration_days=2)
    fs_succ = ts.create_task(pid, "FS Successor", duration_days=1)
    ss_succ = ts.create_task(pid, "SS Successor", duration_days=5)

    ts.add_dependency(pred.id, fs_succ.id, DependencyType.FINISH_TO_START, lag_days=0)
    ts.add_dependency(pred.id, ss_succ.id, DependencyType.START_TO_START, lag_days=0)

    result = sched.recalculate_project_schedule(pid)
    pred_info = result[pred.id]
    fs_info = result[fs_succ.id]
    ss_info = result[ss_succ.id]

    # With lag=0, SS's backward formula propagates the successor's own
    # latest-start straight onto the predecessor: pred.LS == ss_succ.LS.
    # Under the old shadowing bug, pred.LS would instead have come out
    # equal to a looser, FS-derived value (fs_succ.LS shifted back by the
    # predecessor's own duration), strictly LATER than ss_succ.LS.
    assert pred_info.latest_start == ss_info.latest_start
    assert pred_info.latest_start < fs_info.latest_start


def test_schedule_actual_date_constraints_override_computed_dates(services):
    ps = services["project_service"]
    ts = services["task_service"]
    wc = services["work_calendar_engine"]
    sched = services["scheduling_engine"]

    project = ps.create_project("Actual Dates", "")
    pid = project.id
    t = ts.create_task(pid, "Execution Task", start_date=date(2023, 11, 6), duration_days=3)

    ts.update_progress(task_id=t.id, actual_start=date(2023, 11, 8))
    r1 = sched.recalculate_project_schedule(pid)[t.id]
    assert r1.earliest_start == date(2023, 11, 8)
    assert r1.earliest_finish == wc.add_working_days(date(2023, 11, 8), 3)

    ts.update_progress(task_id=t.id, actual_end=date(2023, 11, 14))
    r2 = sched.recalculate_project_schedule(pid)[t.id]
    assert r2.earliest_start == date(2023, 11, 8)
    assert r2.earliest_finish == date(2023, 11, 14)


def test_gantt_data_matches_schedule_and_includes_unscheduled_tasks(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rp = services["reporting_service"]
    sched = services["scheduling_engine"]

    project = ps.create_project("Gantt Math", "")
    pid = project.id

    t1 = ts.create_task(pid, "Planned A", start_date=date(2023, 11, 6), duration_days=2)
    t2 = ts.create_task(pid, "Unscheduled", duration_days=None)
    t3 = ts.create_task(pid, "Planned B", duration_days=1)
    ts.add_dependency(t1.id, t3.id, DependencyType.FINISH_TO_START, lag_days=0)

    schedule = sched.recalculate_project_schedule(pid)
    bars = rp.get_gantt_data(pid)
    by_id = _bar_map(bars)

    assert len(bars) == 3
    assert len({b.task_id for b in bars}) == 3

    for tid, info in schedule.items():
        assert by_id[tid].start == info.earliest_start
        assert by_id[tid].end == info.earliest_finish
        assert by_id[tid].is_critical == info.is_critical

    assert by_id[t2.id].start is None
    assert by_id[t2.id].end is None


def test_gantt_reacts_to_new_dependency_constraints(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rp = services["reporting_service"]
    wc = services["work_calendar_engine"]

    project = ps.create_project("Gantt Dependency Shift", "")
    pid = project.id

    pred = ts.create_task(pid, "Predecessor", start_date=date(2023, 11, 6), duration_days=3)
    succ = ts.create_task(pid, "Successor", start_date=date(2023, 11, 6), duration_days=2)

    before = {b.task_id: b for b in rp.get_gantt_data(pid)}
    assert before[succ.id].start == date(2023, 11, 6)

    ts.add_dependency(pred.id, succ.id, DependencyType.FINISH_TO_START, lag_days=0)

    after = {b.task_id: b for b in rp.get_gantt_data(pid)}
    expected_start = wc.next_working_day(after[pred.id].end, include_today=False)
    assert after[succ.id].start == expected_start
    assert after[succ.id].end == wc.add_working_days(expected_start, 2)
