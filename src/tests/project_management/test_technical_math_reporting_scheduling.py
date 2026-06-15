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

    ss_info = result[ss.id]
    exp_ss_start = wc.add_working_days(p.earliest_start, 3)
    exp_ss_finish = wc.add_working_days(exp_ss_start, 2)
    assert ss_info.earliest_start == exp_ss_start
    assert ss_info.earliest_finish == exp_ss_finish

    ff_info = result[ff.id]
    exp_ff_finish = wc.add_working_days(p.earliest_finish, 2)
    exp_ff_start = wc.add_working_days(exp_ff_finish, -1)
    assert ff_info.earliest_start == exp_ff_start
    assert ff_info.earliest_finish == exp_ff_finish

    sf_info = result[sf.id]
    sf_target_finish = wc.add_working_days(p.earliest_start, 3)
    exp_sf_start = wc.add_working_days(sf_target_finish, -1)
    exp_sf_finish = wc.add_working_days(exp_sf_start, 2)
    assert sf_info.earliest_start == exp_sf_start
    assert sf_info.earliest_finish == exp_sf_finish


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
