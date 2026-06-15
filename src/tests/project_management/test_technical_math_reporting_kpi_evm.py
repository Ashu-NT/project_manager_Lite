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
        currency="USD",
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
