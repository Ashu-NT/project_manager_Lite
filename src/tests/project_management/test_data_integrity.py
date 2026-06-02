"""Tests for the PM read-only data-integrity health checks.

Bad rows are inserted directly via the ORM (simulating legacy data created
before the application-layer guards / unique constraints existed), then the
checker is asserted to detect them. The in-memory `session` fixture enforces
SQLite foreign keys, so these inserts also confirm which invariants the schema
does NOT yet enforce on its own.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from src.core.platform.common.exceptions import ValidationError

from src.core.modules.project_management.infrastructure.persistence.health import (
    run_pm_data_integrity_checks,
)
from src.core.modules.project_management.infrastructure.persistence.orm.baseline import (
    BaselineTaskORM,
    ProjectBaselineORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.cost_calendar import (
    CostItemORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import (
    ProjectORM,
    ProjectResourceORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.resource import (
    ResourceORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.task import (
    TaskAssignmentORM,
    TaskDependencyORM,
    TaskORM,
)


# ── small ORM builders ──────────────────────────────────────────────────────
# These ORM rows have no SQLAlchemy relationship() links, so the unit of work
# does not reorder cross-table INSERTs. Each builder flushes immediately; tests
# always create parents before children, so FK constraints stay satisfied.
def _add(session, row):
    session.add(row)
    session.flush()
    return row


def _project(session, pid):
    return _add(session, ProjectORM(id=pid, name=pid.upper()))


def _task(session, tid, pid):
    return _add(session, TaskORM(id=tid, project_id=pid, name=tid.upper()))


def _resource(session, rid):
    return _add(session, ResourceORM(id=rid, name=rid.upper()))


def _project_resource(session, prid, pid, rid):
    return _add(session, ProjectResourceORM(id=prid, project_id=pid, resource_id=rid))


def _assignment(session, aid, tid, rid, *, project_resource_id=None, allocation=100.0):
    return _add(
        session,
        TaskAssignmentORM(
            id=aid,
            task_id=tid,
            resource_id=rid,
            allocation_percent=allocation,
            project_resource_id=project_resource_id,
        ),
    )


def _dependency(session, did, pred, succ):
    return _add(
        session,
        TaskDependencyORM(id=did, predecessor_task_id=pred, successor_task_id=succ),
    )


def _cost(session, cid, pid, tid):
    return _add(
        session,
        CostItemORM(id=cid, project_id=pid, task_id=tid, description="x", planned_amount=10.0),
    )


def _by_cat(session):
    session.flush()
    report = run_pm_data_integrity_checks(session)
    return report, {f.category: f for f in report.findings}


# ── happy path ──────────────────────────────────────────────────────────────
def test_clean_single_project_reports_ok(session):
    _project(session, "p1")
    _task(session, "t1", "p1")
    report, _ = _by_cat(session)
    assert report.ok
    assert report.problems == ()


def test_fully_valid_same_project_graph_is_ok(session):
    _project(session, "p1")
    _resource(session, "r1")
    _project_resource(session, "pr1", "p1", "r1")
    _task(session, "t1", "p1")
    _task(session, "t2", "p1")
    _assignment(session, "a1", "t1", "r1", project_resource_id="pr1", allocation=50.0)
    _dependency(session, "d1", "t1", "t2")
    _cost(session, "c1", "p1", "t1")
    report, _ = _by_cat(session)
    assert report.ok, report.to_lines()


# ── dependency invariants ───────────────────────────────────────────────────
def test_detects_cross_project_dependency(session):
    _project(session, "p1")
    _project(session, "p2")
    _task(session, "t1", "p1")
    _task(session, "t2", "p2")
    _dependency(session, "d1", "t1", "t2")
    _, by_cat = _by_cat(session)
    assert by_cat["cross_project_dependency"].count == 1
    assert by_cat["cross_project_dependency"].severity == "error"


def test_detects_self_dependency(session):
    _project(session, "p1")
    _task(session, "t1", "p1")
    _dependency(session, "d1", "t1", "t1")
    _, by_cat = _by_cat(session)
    assert by_cat["self_dependency"].count == 1


def test_duplicate_dependency_rejected_by_db(session):
    # ux_task_dependencies_pair (added in migration k4l5m6n7o8p9) blocks dupes
    # at the DB layer; the application layer also raises DEPENDENCY_DUPLICATE.
    _project(session, "p1")
    _task(session, "t1", "p1")
    _task(session, "t2", "p1")
    _dependency(session, "d1", "t1", "t2")
    with pytest.raises(IntegrityError):
        _dependency(session, "d2", "t1", "t2")


# ── assignment invariants ───────────────────────────────────────────────────
def test_detects_assignment_resource_not_in_project(session):
    _project(session, "p1")
    _resource(session, "r1")  # never linked to p1 via project_resources
    _task(session, "t1", "p1")
    _assignment(session, "a1", "t1", "r1")
    _, by_cat = _by_cat(session)
    assert by_cat["assignment_resource_not_in_project"].count == 1


def test_detects_assignment_project_resource_mismatch(session):
    _project(session, "p1")
    _project(session, "p2")
    _resource(session, "r1")
    # project_resource belongs to p2, but the task belongs to p1
    _project_resource(session, "pr2", "p2", "r1")
    _task(session, "t1", "p1")
    _assignment(session, "a1", "t1", "r1", project_resource_id="pr2")
    _, by_cat = _by_cat(session)
    assert by_cat["assignment_project_resource_mismatch"].count == 1


def test_duplicate_assignment_rejected_by_db(session):
    # ux_task_assignments_task_resource blocks (task, resource) dupes at the DB
    # layer; the application layer also raises ASSIGNMENT_DUPLICATE.
    _project(session, "p1")
    _resource(session, "r1")
    _project_resource(session, "pr1", "p1", "r1")
    _task(session, "t1", "p1")
    _assignment(session, "a1", "t1", "r1", project_resource_id="pr1", allocation=10.0)
    with pytest.raises(IntegrityError):
        _assignment(session, "a2", "t1", "r1", project_resource_id="pr1", allocation=10.0)


def test_detects_resource_overallocation(session):
    _project(session, "p1")
    _resource(session, "r1")
    _project_resource(session, "pr1", "p1", "r1")
    _task(session, "t1", "p1")
    _task(session, "t2", "p1")
    _assignment(session, "a1", "t1", "r1", project_resource_id="pr1", allocation=70.0)
    _assignment(session, "a2", "t2", "r1", project_resource_id="pr1", allocation=60.0)
    _, by_cat = _by_cat(session)
    assert by_cat["resource_overallocation"].count == 1
    assert by_cat["resource_overallocation"].severity == "review"


# ── cost invariants ─────────────────────────────────────────────────────────
def test_detects_cost_linked_to_other_project_task(session):
    _project(session, "p1")
    _project(session, "p2")
    _task(session, "t2", "p2")
    # cost belongs to p1 but links a task from p2
    _cost(session, "c1", "p1", "t2")
    _, by_cat = _by_cat(session)
    assert by_cat["cost_task_cross_project"].count == 1


# ── baseline invariants ─────────────────────────────────────────────────────
def test_detects_baseline_task_cross_project(session):
    _project(session, "p1")
    _project(session, "p2")
    _task(session, "t2", "p2")
    _add(session, ProjectBaselineORM(id="b1", project_id="p1", name="B1", created_at=datetime(2026, 1, 1)))
    # baseline belongs to p1, but the snapshotted live task is in p2
    _add(session, BaselineTaskORM(id="bt1", baseline_id="b1", task_id="t2", task_name="T2"))
    _, by_cat = _by_cat(session)
    assert by_cat["baseline_task_cross_project"].count == 1


def test_baseline_snapshot_of_deleted_task_is_not_flagged(session):
    # A baseline task whose live task no longer exists is a normal snapshot,
    # not a cross-project error.
    _project(session, "p1")
    _add(session, ProjectBaselineORM(id="b1", project_id="p1", name="B1", created_at=datetime(2026, 1, 1)))
    _add(session, BaselineTaskORM(id="bt1", baseline_id="b1", task_id="ghost", task_name="Gone"))
    _, by_cat = _by_cat(session)
    assert by_cat["baseline_task_cross_project"].count == 0


# ── service-level guard (friendly error before the DB constraint fires) ──────
def test_assign_resource_twice_raises_assignment_duplicate(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]

    project = ps.create_project("Dup Assign", "")
    task = ts.create_task(project.id, "Task A", start_date=date(2023, 11, 6), duration_days=2)
    resource = rs.create_resource("Dup Dev", "Developer", hourly_rate=100.0)

    ts.assign_resource(task.id, resource.id, allocation_percent=50.0)
    with pytest.raises(ValidationError) as exc:
        ts.assign_resource(task.id, resource.id, allocation_percent=20.0)
    assert exc.value.code == "ASSIGNMENT_DUPLICATE"


# ── report formatting ───────────────────────────────────────────────────────
def test_report_lines_render_problems(session):
    _project(session, "p1")
    _task(session, "t1", "p1")
    _dependency(session, "d1", "t1", "t1")
    report, _ = _by_cat(session)
    text = "\n".join(report.to_lines())
    assert "self_dependency" in text
    assert not report.ok
