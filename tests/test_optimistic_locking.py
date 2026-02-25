from __future__ import annotations

from datetime import date

import pytest

from core.exceptions import ConcurrencyError


def test_project_update_rejects_stale_expected_version(services):
    ps = services["project_service"]

    project = ps.create_project("Lock Project")
    updated = ps.update_project(project.id, name="Lock Project v2")

    assert updated.version == 2
    with pytest.raises(ConcurrencyError):
        ps.update_project(project.id, name="stale", expected_version=1)


def test_task_update_rejects_stale_expected_version(services):
    ps = services["project_service"]
    ts = services["task_service"]

    project = ps.create_project("Task Lock Project")
    task = ts.create_task(
        project.id,
        "Task A",
        start_date=date(2026, 2, 24),
        duration_days=2,
    )
    updated = ts.update_task(task.id, name="Task A v2")

    assert updated.version == 2
    with pytest.raises(ConcurrencyError):
        ts.update_task(task.id, name="stale", expected_version=1)


def test_resource_update_rejects_stale_expected_version(services):
    rs = services["resource_service"]

    resource = rs.create_resource("Dev A", hourly_rate=100.0)
    updated = rs.update_resource(resource.id, role="Engineer")

    assert updated.version == 2
    with pytest.raises(ConcurrencyError):
        rs.update_resource(resource.id, role="stale", expected_version=1)


def test_cost_update_rejects_stale_expected_version(services):
    ps = services["project_service"]
    cs = services["cost_service"]

    project = ps.create_project("Cost Lock Project")
    item = cs.add_cost_item(
        project_id=project.id,
        description="Travel",
        planned_amount=1000.0,
    )
    updated = cs.update_cost_item(item.id, actual_amount=250.0)

    assert updated.version == 2
    with pytest.raises(ConcurrencyError):
        cs.update_cost_item(item.id, actual_amount=300.0, expected_version=1)

