from datetime import date

from core.exceptions import NotFoundError
from infra.db.repositories import SqlAlchemyAssignmentRepository, SqlAlchemyDependencyRepository


def test_cost_summary_has_legacy_and_normalized_keys(services):
    ps = services["project_service"]
    ts = services["task_service"]
    cost_s = services["cost_service"]

    project = ps.create_project("Cost Summary Keys", "")
    pid = project.id

    task = ts.create_task(pid, "Cost Task", duration_days=1)
    cost_s.add_cost_item(
        project_id=pid,
        description="One item",
        planned_amount=100.0,
        committed_amount=20.0,
        actual_amount=10.0,
        task_id=task.id,
    )

    summary = cost_s.get_project_cost_summary(pid)

    assert summary["total_planned"] == 100.0
    assert summary["total_committed"] == 20.0
    assert summary["total-committed"] == 20.0
    assert summary["total_actual"] == 10.0
    assert summary["variance"] == -90.0
    assert summary["variance_actual"] == -90.0
    assert summary["variance_commitment"] == -80.0
    assert summary["variance_committment"] == -80.0


def test_dashboard_high_priority_without_deadline_does_not_crash(services):
    ps = services["project_service"]
    ts = services["task_service"]
    ds = services["dashboard_service"]

    project = ps.create_project("Dashboard Priority", "")
    pid = project.id

    ts.create_task(
        pid,
        "High Priority No Deadline",
        start_date=date(2023, 11, 6),
        duration_days=2,
        priority=90,
    )

    data = ds.get_dashboard_data(pid)
    assert data.kpi.project_id == pid
    assert not any("High-priority task" in msg for msg in data.alerts)


def test_baseline_variance_marks_critical_tasks(services):
    ps = services["project_service"]
    ts = services["task_service"]
    baseline_s = services["baseline_service"]
    reporting_s = services["reporting_service"]

    project = ps.create_project("Variance Critical", "")
    pid = project.id

    t = ts.create_task(pid, "Only Task", start_date=date(2023, 11, 6), duration_days=2)
    baseline = baseline_s.create_baseline(pid, "B1")

    rows = reporting_s.get_baseline_schedule_variance(pid, baseline_id=baseline.id)
    assert len(rows) == 1
    assert rows[0].task_id == t.id
    assert rows[0].is_critical is True


def test_dependency_repository_filters_by_project(session, services):
    ps = services["project_service"]
    ts = services["task_service"]

    p1 = ps.create_project("Dep P1", "")
    p2 = ps.create_project("Dep P2", "")

    a1 = ts.create_task(p1.id, "A1", start_date=date(2023, 11, 6), duration_days=1)
    b1 = ts.create_task(p1.id, "B1", duration_days=1)
    a2 = ts.create_task(p2.id, "A2", start_date=date(2023, 11, 6), duration_days=1)
    b2 = ts.create_task(p2.id, "B2", duration_days=1)

    ts.add_dependency(a1.id, b1.id)
    ts.add_dependency(a2.id, b2.id)

    dep_repo = SqlAlchemyDependencyRepository(session)
    deps_p1 = dep_repo.list_by_project(p1.id)
    deps_p2 = dep_repo.list_by_project(p2.id)

    assert len(deps_p1) == 1
    assert len(deps_p2) == 1
    assert deps_p1[0].predecessor_task_id == a1.id
    assert deps_p2[0].predecessor_task_id == a2.id


def test_remove_dependency_raises_not_found(services):
    ts = services["task_service"]
    try:
        ts.remove_dependency("missing-dependency-id")
        assert False, "Expected NotFoundError for missing dependency"
    except NotFoundError as exc:
        assert exc.code == "DEPENDENCY_NOT_FOUND"


def test_assignment_repository_list_by_tasks_returns_domain_models(session, services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]

    p = ps.create_project("Assignment Mapping", "")
    t = ts.create_task(p.id, "Task A", start_date=date(2023, 11, 6), duration_days=2)
    r = rs.create_resource("Dev 1", "Developer", hourly_rate=100.0)
    created = ts.assign_resource(t.id, r.id, allocation_percent=50.0)

    repo = SqlAlchemyAssignmentRepository(session)
    rows = repo.list_by_tasks([t.id])

    assert len(rows) == 1
    assert rows[0].id == created.id
    assert rows[0].__class__.__name__ == "TaskAssignment"
