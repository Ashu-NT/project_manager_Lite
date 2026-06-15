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
    source = rp.get_project_cost_source_breakdown(pid)
    rows = {r.source_key: r for r in source.rows}
    assert rows["DIRECT_COST"].actual == pytest.approx(0.0)
    assert rows["COMPUTED_LABOR"].actual == pytest.approx(0.0)
    assert rows["LABOR_ADJUSTMENT"].actual == pytest.approx(80.0)

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
    source = rp.get_project_cost_source_breakdown(pid, as_of=date(2023, 11, 30))
    rows = {r.source_key: r for r in source.rows}
    assert rows["DIRECT_COST"].actual == pytest.approx(30.0)
    assert rows["COMPUTED_LABOR"].actual == pytest.approx(200.0)
    assert rows["LABOR_ADJUSTMENT"].actual == pytest.approx(0.0)
    assert source.notes

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
