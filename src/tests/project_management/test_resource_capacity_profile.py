from datetime import date

import pytest

from src.core.modules.project_management.application.resources import (
    ResourceUtilizationBand,
    is_resource_near_capacity,
    is_resource_overloaded,
    resource_utilization_band,
)


@pytest.mark.parametrize(
    ("utilization", "expected"),
    (
        (0.0, ResourceUtilizationBand.IDLE),
        (84.9, ResourceUtilizationBand.STABLE),
        (85.0, ResourceUtilizationBand.HOT),
        (89.9, ResourceUtilizationBand.HOT),
        (90.0, ResourceUtilizationBand.NEAR_CAPACITY),
        (100.0, ResourceUtilizationBand.NEAR_CAPACITY),
        (100.1, ResourceUtilizationBand.OVERLOADED),
    ),
)
def test_resource_utilization_policy_has_canonical_boundaries(
    utilization,
    expected,
) -> None:
    assert resource_utilization_band(utilization) is expected
    assert is_resource_overloaded(utilization) is (
        expected is ResourceUtilizationBand.OVERLOADED
    )
    assert is_resource_near_capacity(utilization) is (
        expected is ResourceUtilizationBand.NEAR_CAPACITY
    )


def test_resource_profile_fields_roundtrip(services):
    rs = services["resource_service"]

    created = rs.create_resource(
        "Capacity Resource",
        role="Developer",
        hourly_rate=90.0,
        capacity_percent=80.0,
        address="Berlin Office",
        contact="cap.resource@example.com",
    )
    assert created.capacity_percent == pytest.approx(80.0)
    assert created.address == "Berlin Office"
    assert created.contact == "cap.resource@example.com"

    updated = rs.update_resource(
        resource_id=created.id,
        expected_version=created.version,
        name=created.name,
        code=created.code,
        kind=created.kind,
        role=created.role,
        hourly_rate=created.hourly_rate,
        cost_type=created.cost_type,
        currency_code=created.currency_code,
        capacity_percent=120.0,
        address="Remote",
        contact="updated@example.com",
        worker_type=created.worker_type,
        employee_id=created.employee_id,
        department_id=created.department_id,
        site_id=created.site_id,
    )
    assert updated.capacity_percent == pytest.approx(120.0)
    assert updated.address == "Remote"
    assert updated.contact == "updated@example.com"

    fetched = rs.get_resource(created.id)
    assert fetched.capacity_percent == pytest.approx(120.0)
    assert fetched.address == "Remote"
    assert fetched.contact == "updated@example.com"


def test_assignment_overallocation_uses_resource_capacity(services):
    """60% + 30% = 90% of nominal capacity, but this resource's
    capacity_percent=80.0 narrows the effective ceiling, so the combined
    commitment (90% of nominal hours against an 80%-of-nominal ceiling =
    112.5% of effective capacity) is genuinely over -- proving
    Resource.capacity_percent is actually applied by the calendar-based
    capacity authority (docs §44), not just carried as inert metadata."""
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]

    project = ps.create_project("Capacity Allocation Rules", "")
    t1 = ts.create_task(project.id, "Task One", start_date=date(2024, 1, 2), duration_days=2)
    t2 = ts.create_task(project.id, "Task Two", start_date=date(2024, 1, 2), duration_days=2)
    resource = rs.create_resource("Capacity Dev", "Developer", capacity_percent=80.0)

    ts.assign_resource(t1.id, resource.id, allocation_percent=60.0)
    ts.assign_resource(t2.id, resource.id, allocation_percent=30.0)
    warning = ts.consume_last_overallocation_warning()
    assert warning is not None
    assert "112.5%" in warning


def test_resource_load_summary_reports_capacity_and_utilization(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    rp = services["reporting_service"]

    project = ps.create_project("Capacity Load Summary", "")
    t1 = ts.create_task(project.id, "Task A", start_date=date(2024, 1, 2), duration_days=2)
    t2 = ts.create_task(project.id, "Task B", start_date=date(2024, 1, 2), duration_days=2)
    resource = rs.create_resource("Load Resource", "Dev", capacity_percent=80.0)

    ts.assign_resource(t1.id, resource.id, allocation_percent=50.0)
    ts.assign_resource(t2.id, resource.id, allocation_percent=30.0)

    rows = rp.get_resource_load_summary(project.id)
    row = next(r for r in rows if r.resource_id == resource.id)
    assert row.capacity_percent == pytest.approx(80.0)
    assert row.total_allocation_percent == pytest.approx(80.0)
    assert row.utilization_percent == pytest.approx(100.0)


def test_resource_load_summary_uses_peak_concurrent_allocation(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    rp = services["reporting_service"]

    project = ps.create_project("Peak Resource Load", "")
    t1 = ts.create_task(project.id, "Seq A", start_date=date(2024, 1, 2), duration_days=2)
    t2 = ts.create_task(project.id, "Seq B", start_date=date(2024, 1, 8), duration_days=2)
    resource = rs.create_resource("Peak Dev", "Dev", capacity_percent=100.0)

    ts.assign_resource(t1.id, resource.id, allocation_percent=60.0)
    ts.assign_resource(t2.id, resource.id, allocation_percent=60.0)

    rows = rp.get_resource_load_summary(project.id)
    row = next(r for r in rows if r.resource_id == resource.id)
    assert row.total_allocation_percent == pytest.approx(60.0)
    assert row.utilization_percent == pytest.approx(60.0)

