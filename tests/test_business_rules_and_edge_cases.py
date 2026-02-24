from datetime import date

import pytest

from core.exceptions import BusinessRuleError, NotFoundError, ValidationError
from core.models import DependencyType


def test_task_name_validation_rules(services):
    ps = services["project_service"]
    ts = services["task_service"]

    project = ps.create_project("Task Name Rules", "")
    pid = project.id

    with pytest.raises(ValidationError) as exc_short:
        ts.create_task(pid, "AB", duration_days=1)
    assert exc_short.value.code == "TASK_NAME_TOO_SHORT"

    with pytest.raises(ValidationError) as exc_bad_chars:
        ts.create_task(pid, "Bad/Name", duration_days=1)
    assert exc_bad_chars.value.code == "TASK_NAME_INVALID_CHARS"

    with pytest.raises(ValidationError) as exc_empty:
        ts.create_task(pid, "   ", duration_days=1)
    assert exc_empty.value.code == "TASK_NAME_EMPTY"


def test_task_dates_must_fit_project_window(services):
    ps = services["project_service"]
    ts = services["task_service"]

    project = ps.create_project(
        "Project Date Window",
        "",
        start_date=date(2023, 11, 10),
        end_date=date(2023, 11, 20),
    )
    pid = project.id

    with pytest.raises(ValidationError) as exc_before:
        ts.create_task(pid, "Too Early", start_date=date(2023, 11, 9), duration_days=1)
    assert exc_before.value.code == "TASK_INVALID_DATE"

    with pytest.raises(ValidationError) as exc_after:
        ts.create_task(pid, "Too Late", start_date=date(2023, 11, 21), duration_days=1)
    assert exc_after.value.code == "TASK_INVALID_DATE"

    ok = ts.create_task(pid, "Within Range", start_date=date(2023, 11, 13), duration_days=2)
    assert ok.id


def test_dependency_cross_project_and_duplicate_rules(services):
    ps = services["project_service"]
    ts = services["task_service"]

    p1 = ps.create_project("Deps P1", "")
    p2 = ps.create_project("Deps P2", "")

    a = ts.create_task(p1.id, "Alpha", start_date=date(2023, 11, 6), duration_days=1)
    b = ts.create_task(p1.id, "Bravo", duration_days=1)
    c = ts.create_task(p2.id, "Charlie", duration_days=1)

    ts.add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)

    with pytest.raises(ValidationError) as exc_dup:
        ts.add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)
    assert exc_dup.value.code == "DEPENDENCY_DUPLICATE"

    with pytest.raises(ValidationError) as exc_cross:
        ts.add_dependency(a.id, c.id, DependencyType.FINISH_TO_START, lag_days=0)
    assert exc_cross.value.code == "DEPENDENCY_CROSS_PROJECT"


def test_assignment_allocation_and_resource_validation(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]

    project = ps.create_project("Assign Rules", "")
    pid = project.id
    task = ts.create_task(pid, "Assignable Task", start_date=date(2023, 11, 6), duration_days=2)
    resource = rs.create_resource("Assignable Dev", "Developer", hourly_rate=100.0)

    with pytest.raises(ValidationError):
        ts.assign_resource(task.id, resource.id, allocation_percent=0.0)
    with pytest.raises(ValidationError):
        ts.assign_resource(task.id, resource.id, allocation_percent=120.0)
    with pytest.raises(NotFoundError):
        ts.assign_resource(task.id, "missing-resource-id", allocation_percent=50.0)


def test_query_tasks_requires_project_id(services):
    ts = services["task_service"]
    with pytest.raises(ValidationError):
        ts.query_tasks(project_id=None)


def test_work_calendar_next_and_negative_day_math(services):
    wc_s = services["work_calendar_service"]
    wc = services["work_calendar_engine"]

    wc_s.set_working_days({0, 1, 2, 3, 4}, hours_per_day=8.0)

    # Saturday -> next working day Monday
    assert wc.next_working_day(date(2023, 11, 4), include_today=True) == date(2023, 11, 6)

    # One day backward from Monday -> previous Friday
    assert wc.add_working_days(date(2023, 11, 6), -1) == date(2023, 11, 3)

    # Holiday should be skipped
    wc_s.add_holiday(date(2023, 11, 6), "Holiday Monday")
    assert wc.next_working_day(date(2023, 11, 4), include_today=True) == date(2023, 11, 7)


def test_calendar_event_update_rejects_end_before_start(services):
    cal = services["calendar_service"]

    ev = cal.create_event(
        title="Planning Session",
        start_date=date(2023, 11, 10),
        end_date=date(2023, 11, 12),
        description="Initial plan",
    )

    with pytest.raises(ValidationError):
        cal.update_event(ev.id, end_date=date(2023, 11, 9))


def test_cost_service_negative_amount_validation(services):
    ps = services["project_service"]
    ts = services["task_service"]
    cs = services["cost_service"]

    project = ps.create_project("Cost Validation", "")
    pid = project.id
    task = ts.create_task(pid, "Cost Task", duration_days=1)

    with pytest.raises(ValidationError):
        cs.add_cost_item(pid, "Bad planned", planned_amount=-1.0, task_id=task.id)
    with pytest.raises(ValidationError):
        cs.add_cost_item(pid, "Bad committed", planned_amount=1.0, committed_amount=-1.0, task_id=task.id)
    with pytest.raises(ValidationError):
        cs.add_cost_item(pid, "Bad actual", planned_amount=1.0, actual_amount=-1.0, task_id=task.id)

    item = cs.add_cost_item(pid, "Valid", planned_amount=10.0, task_id=task.id)
    with pytest.raises(ValidationError):
        cs.update_cost_item(item.id, actual_amount=-5.0)


def test_baseline_requires_tasks_and_budget_fallback_affects_bac(services):
    ps = services["project_service"]
    ts = services["task_service"]
    bs = services["baseline_service"]
    rp = services["reporting_service"]

    no_task_project = ps.create_project("No Tasks Baseline", "")
    with pytest.raises(ValidationError):
        bs.create_baseline(no_task_project.id, "BL-Empty")

    budget_project = ps.create_project(
        "Budget Baseline",
        "",
        planned_budget=1000.0,
        start_date=date(2023, 11, 6),
        end_date=date(2023, 11, 20),
    )
    pid = budget_project.id
    ts.create_task(pid, "Budgeted Task", start_date=date(2023, 11, 6), duration_days=3)
    baseline = bs.create_baseline(pid, "BL-Budget")

    evm = rp.get_earned_value(project_id=pid, baseline_id=baseline.id, as_of=date(2023, 11, 30))
    assert evm.BAC == pytest.approx(1000.0)


def test_reporting_earned_value_requires_baseline(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rp = services["reporting_service"]

    project = ps.create_project("No Baseline EVM", "")
    pid = project.id
    ts.create_task(pid, "Any Task", start_date=date(2023, 11, 6), duration_days=1)

    with pytest.raises(BusinessRuleError) as exc:
        rp.get_earned_value(pid)
    assert exc.value.code == "NO_BASELINE"


def test_dashboard_returns_none_evm_without_baseline(services):
    ps = services["project_service"]
    ts = services["task_service"]
    ds = services["dashboard_service"]

    project = ps.create_project("Dashboard No Baseline", "")
    pid = project.id
    ts.create_task(pid, "Dash Task", start_date=date(2023, 11, 6), duration_days=2)

    data = ds.get_dashboard_data(pid)
    assert data.evm is None


def test_resource_load_summary_sorted_descending(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    rp = services["reporting_service"]

    project = ps.create_project("Resource Load Sort", "")
    pid = project.id
    t1 = ts.create_task(pid, "Task One", start_date=date(2023, 11, 6), duration_days=2)
    t2 = ts.create_task(pid, "Task Two", start_date=date(2023, 11, 6), duration_days=2)

    r1 = rs.create_resource("Res One", "Dev", hourly_rate=100.0)
    r2 = rs.create_resource("Res Two", "QA", hourly_rate=100.0)

    ts.assign_resource(t1.id, r1.id, allocation_percent=20.0)
    ts.assign_resource(t2.id, r2.id, allocation_percent=80.0)

    rows = rp.get_resource_load_summary(pid)
    assert len(rows) == 2
    assert rows[0].total_allocation_percent >= rows[1].total_allocation_percent


def test_dependency_diagnostics_flags_duplicates(services):
    ps = services["project_service"]
    ts = services["task_service"]

    project = ps.create_project("Dependency Diagnostics", "")
    t1 = ts.create_task(project.id, "Task A", start_date=date(2023, 11, 6), duration_days=1)
    t2 = ts.create_task(project.id, "Task B", start_date=date(2023, 11, 6), duration_days=1)
    ts.add_dependency(t1.id, t2.id, DependencyType.FINISH_TO_START, lag_days=0)

    diag = ts.get_dependency_diagnostics(t1.id, t2.id, include_impact=False)
    assert not diag.is_valid
    assert diag.code == "DEPENDENCY_DUPLICATE"


def test_dependency_diagnostics_cycle_includes_path_names(services):
    ps = services["project_service"]
    ts = services["task_service"]

    project = ps.create_project("Cycle Detail", "")
    task_a = ts.create_task(project.id, "Task A", start_date=date(2023, 11, 6), duration_days=1)
    task_b = ts.create_task(project.id, "Task B", duration_days=1)
    task_c = ts.create_task(project.id, "Task C", duration_days=1)
    ts.add_dependency(task_a.id, task_b.id, DependencyType.FINISH_TO_START, lag_days=0)
    ts.add_dependency(task_b.id, task_c.id, DependencyType.FINISH_TO_START, lag_days=0)

    diag = ts.get_dependency_diagnostics(task_c.id, task_a.id, include_impact=False)
    assert not diag.is_valid
    assert diag.code == "DEPENDENCY_CYCLE"
    assert "Task A" in diag.detail
    assert "Task B" in diag.detail
    assert "Task C" in diag.detail


def test_dependency_diagnostics_reports_schedule_impact(services):
    ps = services["project_service"]
    ts = services["task_service"]

    project = ps.create_project("Impact Preview", "")
    task_a = ts.create_task(project.id, "Task A", start_date=date(2023, 11, 6), duration_days=2)
    task_b = ts.create_task(project.id, "Task B", start_date=date(2023, 11, 6), duration_days=2)

    diag = ts.get_dependency_diagnostics(
        task_a.id,
        task_b.id,
        dependency_type=DependencyType.FINISH_TO_START,
        lag_days=0,
        include_impact=True,
    )
    assert diag.is_valid
    assert any(row.task_id == task_b.id for row in diag.impact_rows)
    impacted_b = next(row for row in diag.impact_rows if row.task_id == task_b.id)
    assert (impacted_b.start_shift_days or 0) > 0
    assert "Task B" in impacted_b.trace_path


def test_add_dependency_uses_diagnostics_for_cycle_rule(services):
    ps = services["project_service"]
    ts = services["task_service"]

    project = ps.create_project("Cycle Enforcement", "")
    t1 = ts.create_task(project.id, "Task 1", start_date=date(2023, 11, 6), duration_days=1)
    t2 = ts.create_task(project.id, "Task 2", duration_days=1)
    ts.add_dependency(t1.id, t2.id, DependencyType.FINISH_TO_START, lag_days=0)

    with pytest.raises(BusinessRuleError) as exc:
        ts.add_dependency(t2.id, t1.id, DependencyType.FINISH_TO_START, lag_days=0)
    assert exc.value.code == "DEPENDENCY_CYCLE"
    assert "Cycle path" in str(exc.value)
