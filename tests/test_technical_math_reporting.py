from datetime import date

import pytest

from core.models import CostType, DependencyType, TaskStatus


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


def test_reporting_kpi_math_counts_duration_and_costs(services):
    ps = services["project_service"]
    ts = services["task_service"]
    cs = services["cost_service"]
    rp = services["reporting_service"]

    project = ps.create_project(
        "KPI Math",
        start_date=date(2023, 11, 6),
        end_date=date(2023, 11, 10),
        currency="USD",
    )
    pid = project.id

    t_done = ts.create_task(pid, "Done", start_date=date(2023, 11, 6), duration_days=1)
    t_ip = ts.create_task(pid, "In Progress", start_date=date(2023, 11, 7), duration_days=1)
    t_blocked = ts.create_task(pid, "Blocked", start_date=date(2023, 11, 8), duration_days=1)
    ts.create_task(pid, "Todo", start_date=date(2023, 11, 9), duration_days=1)

    ts.update_task(t_done.id, status=TaskStatus.DONE)
    ts.update_task(t_ip.id, status=TaskStatus.IN_PROGRESS)
    ts.update_task(t_blocked.id, status=TaskStatus.BLOCKED)

    cs.add_cost_item(
        project_id=pid,
        description="C1",
        planned_amount=100.0,
        committed_amount=40.0,
        actual_amount=30.0,
        currency_code="USD",
    )
    cs.add_cost_item(
        project_id=pid,
        description="C2",
        planned_amount=200.0,
        committed_amount=100.0,
        actual_amount=90.0,
        currency_code="USD",
    )

    kpi = rp.get_project_kpis(pid)
    assert kpi.tasks_total == 4
    assert kpi.tasks_completed == 1
    assert kpi.tasks_in_progress == 1
    assert kpi.task_blocked == 1
    assert kpi.tasks_not_started == 1
    assert kpi.duration_working_days == 5

    assert kpi.total_planned_cost == pytest.approx(300.0)
    assert kpi.total_committed_cost == pytest.approx(140.0)
    assert kpi.total_actual_cost == pytest.approx(120.0)
    assert kpi.cost_variance == pytest.approx(-180.0)
    assert kpi.committment_variance == pytest.approx(-160.0)


def test_reporting_evm_core_formulae_and_series_points(services):
    ps = services["project_service"]
    ts = services["task_service"]
    cs = services["cost_service"]
    bs = services["baseline_service"]
    rp = services["reporting_service"]

    project = ps.create_project(
        "EVM Math",
        start_date=date(2023, 11, 6),
        end_date=date(2023, 11, 30),
    )
    pid = project.id
    task = ts.create_task(pid, "Task E", start_date=date(2023, 11, 6), duration_days=2)

    cost = cs.add_cost_item(
        project_id=pid,
        task_id=task.id,
        description="Planned work package",
        planned_amount=100.0,
        actual_amount=0.0,
        currency_code="USD",
    )
    cs.update_cost_item(cost.id, actual_amount=40.0)

    baseline = bs.create_baseline(pid, "BL1")
    ts.update_progress(task.id, percent_complete=50.0)

    evm = rp.get_earned_value(project_id=pid, baseline_id=baseline.id, as_of=date(2023, 11, 30))
    assert evm.baseline_id == baseline.id
    assert evm.BAC == pytest.approx(100.0)
    assert evm.PV == pytest.approx(100.0)
    assert evm.EV == pytest.approx(50.0)
    assert evm.AC == pytest.approx(40.0)

    assert evm.CPI == pytest.approx(1.25)
    assert evm.SPI == pytest.approx(0.5)
    assert evm.EAC == pytest.approx(80.0)
    assert evm.ETC == pytest.approx(40.0)
    assert evm.VAC == pytest.approx(20.0)

    series = rp.get_evm_series(project_id=pid, baseline_id=baseline.id, as_of=date(2023, 12, 15))
    assert len(series) >= 2
    assert series[-1].period_end == date(2023, 12, 31)
    assert all(series[i].period_end <= series[i + 1].period_end for i in range(len(series) - 1))


def test_cost_breakdown_excludes_manual_labor_actual_when_computed_labor_exists(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    cs = services["cost_service"]
    rp = services["reporting_service"]

    project = ps.create_project("Cost Breakdown Math", currency="USD")
    pid = project.id

    task = ts.create_task(pid, "Labor Task", start_date=date(2023, 11, 6), duration_days=2)
    resource = rs.create_resource("Engineer", role="DEV", hourly_rate=100.0, currency_code="USD")
    assignment = ts.assign_resource(task.id, resource.id, allocation_percent=100.0)
    ts.set_assignment_hours(assignment.id, 2.0)  # computed labor = 200

    cs.add_cost_item(
        project_id=pid,
        task_id=task.id,
        description="Manual labor line",
        planned_amount=300.0,
        actual_amount=500.0,
        cost_type=CostType.LABOR,
        currency_code="USD",
    )
    cs.add_cost_item(
        project_id=pid,
        task_id=task.id,
        description="Overhead line",
        planned_amount=100.0,
        actual_amount=30.0,
        cost_type=CostType.OVERHEAD,
        currency_code="USD",
    )

    rows = rp.get_cost_breakdown(project_id=pid, as_of=date(2023, 11, 30))
    labor_planned = _row_sum(rows, "LABOR", "planned")
    labor_actual = _row_sum(rows, "LABOR", "actual")
    overhead_actual = _row_sum(rows, "OVERHEAD", "actual")

    # Planned still reflects planned cost items; actual labor uses computed assignment labor only.
    assert labor_planned == pytest.approx(300.0)
    assert labor_actual == pytest.approx(200.0)
    assert overhead_actual == pytest.approx(30.0)


def test_cost_policy_uses_manual_labor_as_fallback_when_no_computed_labor(services):
    ps = services["project_service"]
    ts = services["task_service"]
    cs = services["cost_service"]
    bs = services["baseline_service"]
    rp = services["reporting_service"]

    project = ps.create_project(
        "Manual Labor Fallback",
        start_date=date(2023, 11, 6),
        end_date=date(2023, 11, 30),
        currency="USD",
    )
    pid = project.id
    task = ts.create_task(pid, "Fallback Task", start_date=date(2023, 11, 6), duration_days=2)

    cs.add_cost_item(
        project_id=pid,
        task_id=task.id,
        description="Manual labor fallback",
        planned_amount=300.0,
        committed_amount=120.0,
        actual_amount=80.0,
        cost_type=CostType.LABOR,
        currency_code="USD",
    )

    totals = rp.get_project_cost_control_totals(pid)
    assert totals.planned == pytest.approx(300.0)
    assert totals.committed == pytest.approx(120.0)
    assert totals.actual == pytest.approx(80.0)

    kpi = rp.get_project_kpis(pid)
    assert kpi.total_planned_cost == pytest.approx(300.0)
    assert kpi.total_committed_cost == pytest.approx(120.0)
    assert kpi.total_actual_cost == pytest.approx(80.0)

    baseline = bs.create_baseline(pid, "BL-Manual")
    evm = rp.get_earned_value(project_id=pid, baseline_id=baseline.id, as_of=date(2023, 11, 30))
    assert evm.BAC == pytest.approx(300.0)


def test_cost_policy_consistent_across_kpi_evm_breakdown_and_totals(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    prs = services["project_resource_service"]
    cs = services["cost_service"]
    bs = services["baseline_service"]
    rp = services["reporting_service"]

    project = ps.create_project(
        "Policy Consistency",
        start_date=date(2023, 11, 6),
        end_date=date(2023, 11, 30),
        currency="USD",
    )
    pid = project.id
    task = ts.create_task(pid, "Execution Task", start_date=date(2023, 11, 6), duration_days=3)

    resource = rs.create_resource("Engineer", role="DEV", hourly_rate=100.0, currency_code="USD")
    pr = prs.add_to_project(
        project_id=pid,
        resource_id=resource.id,
        planned_hours=10.0,
        hourly_rate=100.0,
        currency_code="USD",
    )
    assignment = ts.assign_project_resource(
        task_id=task.id,
        project_resource_id=pr.id,
        allocation_percent=100.0,
    )
    ts.set_assignment_hours(assignment.id, 2.0)  # computed actual labor = 200

    cs.add_cost_item(
        project_id=pid,
        task_id=task.id,
        description="Manual labor adjustment",
        planned_amount=300.0,
        committed_amount=400.0,
        actual_amount=500.0,
        cost_type=CostType.LABOR,
        currency_code="USD",
    )
    cs.add_cost_item(
        project_id=pid,
        task_id=task.id,
        description="Overhead",
        planned_amount=150.0,
        committed_amount=20.0,
        actual_amount=30.0,
        cost_type=CostType.OVERHEAD,
        currency_code="USD",
    )
    cs.add_cost_item(
        project_id=pid,
        task_id=task.id,
        description="Future overhead",
        planned_amount=0.0,
        committed_amount=0.0,
        actual_amount=90.0,
        cost_type=CostType.OVERHEAD,
        currency_code="USD",
        incurred_date=date(2099, 1, 1),
    )

    totals = rp.get_project_cost_control_totals(pid, as_of=date(2023, 11, 30))
    assert totals.planned == pytest.approx(1150.0)  # 1000 computed labor + 150 overhead
    assert totals.committed == pytest.approx(20.0)  # manual labor committed excluded
    assert totals.actual == pytest.approx(230.0)  # 200 computed labor + 30 overhead
    assert totals.exposure == pytest.approx(230.0)

    kpi = rp.get_project_kpis(pid)
    assert kpi.total_planned_cost == pytest.approx(1150.0)
    assert kpi.total_committed_cost == pytest.approx(20.0)
    assert kpi.total_actual_cost == pytest.approx(230.0)

    baseline = bs.create_baseline(pid, "BL-Policy")
    evm = rp.get_earned_value(project_id=pid, baseline_id=baseline.id, as_of=date(2023, 11, 30))
    assert evm.BAC == pytest.approx(1150.0)
    assert evm.AC == pytest.approx(230.0)

    rows = rp.get_cost_breakdown(project_id=pid, as_of=date(2023, 11, 30), baseline_id=baseline.id)
    assert _row_sum(rows, "LABOR", "planned") == pytest.approx(1000.0)
    assert _row_sum(rows, "LABOR", "actual") == pytest.approx(200.0)
    assert _row_sum(rows, "OVERHEAD", "actual") == pytest.approx(30.0)
