from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date, timedelta
from pathlib import Path

import pytest

from src.core.modules.project_management.api.desktop.resources.factories.resources_api_factory import (
    build_project_management_resources_desktop_api,
)
from src.core.modules.project_management.contracts.reads.resources import (
    ResourceWorkloadDemandFact,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError
from src.core.platform.domain.security.auth.session import UserSessionPrincipal


def test_resource_workload_demand_fact_is_immutable() -> None:
    fact = ResourceWorkloadDemandFact(
        assignment_id="assignment-1",
        task_id="task-1",
        project_id="project-1",
        task_start=date(2026, 1, 1),
        task_end=date(2026, 1, 2),
        allocation_percent=50,
        allocated_planned_hours=8,
    )

    with pytest.raises(FrozenInstanceError):
        fact.project_id = "project-2"  # type: ignore[misc]


def test_resource_workload_reads_only_overlapping_assignment_demand(services) -> None:
    project_service = services["project_service"]
    task_service = services["task_service"]
    resource_service = services["resource_service"]
    workload_service = services["resource_workload_service"]
    window_start = date.today() + timedelta(days=1)
    window_end = window_start + timedelta(days=6)

    project = project_service.create_project("R5D bounded workload")
    resource = resource_service.create_resource("R5D bounded resource")
    inside = task_service.create_task(
        project.id,
        "Inside range",
        start_date=window_start,
        duration_days=3,
    )
    outside = task_service.create_task(
        project.id,
        "Outside range",
        start_date=window_end + timedelta(days=30),
        duration_days=3,
    )
    task_service.assign_resource(inside.id, resource.id, allocation_percent=50.0)
    task_service.assign_resource(outside.id, resource.id, allocation_percent=90.0)

    result = workload_service.read(
        resource.id,
        start_date=window_start,
        end_date=window_end,
    )

    assert result.assignment_count == 1
    assert result.project_count == 1
    assert result.planned_commitment_hours > 0
    assert len(result.days) == 7


def test_resource_availability_rejects_invalid_and_unbounded_ranges(services) -> None:
    resource = services["resource_service"].create_resource("R5D range resource")
    api = build_project_management_resources_desktop_api(
        resource_service=services["resource_service"],
        workload_service=services["resource_workload_service"],
    )

    with pytest.raises(ValidationError) as invalid:
        api.build_resource_availability(
            resource.id,
            start_date="not-a-date",
            end_date="2026-12-31",
        )
    assert invalid.value.code == "RESOURCE_WORKLOAD_DATE_REQUIRED"

    with pytest.raises(ValidationError) as too_large:
        api.build_resource_availability(
            resource.id,
            start_date="2026-01-01",
            end_date="2027-01-02",
        )
    assert too_large.value.code == "RESOURCE_WORKLOAD_RANGE_TOO_LARGE"


def test_resource_workload_requires_resource_read(services) -> None:
    resource = services["resource_service"].create_resource("R5D protected resource")
    user_session = services["user_session"]
    original = user_session.principal
    assert original is not None
    user_session.set_principal(
        UserSessionPrincipal(
            user_id=original.user_id,
            username=original.username,
            display_name=original.display_name,
            role_names=frozenset(),
            permissions=frozenset({"organization.access"}),
            scoped_access=original.scoped_access,
            active_tenant_id=original.active_tenant_id,
            active_organization_id=original.active_organization_id,
        )
    )
    try:
        with pytest.raises(BusinessRuleError) as denied:
            services["resource_workload_service"].read(
                resource.id,
                start_date=date.today(),
                end_date=date.today() + timedelta(days=6),
            )
        assert denied.value.code == "PERMISSION_DENIED"
    finally:
        user_session.set_principal(original)


def test_resource_workload_fails_closed_after_organization_switch(services) -> None:
    resource = services["resource_service"].create_resource("R5D scoped resource")
    organization_service = services["organization_service"]
    original = organization_service.get_active_organization()
    other = organization_service.create_organization(
        organization_code="R5D-OTHER",
        display_name="R5D Other Organization",
        base_currency="EUR",
        is_active=False,
    )
    organization_service.set_active_organization(other.id)
    try:
        with pytest.raises(NotFoundError):
            services["resource_workload_service"].read(
                resource.id,
                start_date=date.today(),
                end_date=date.today() + timedelta(days=6),
            )
    finally:
        organization_service.set_active_organization(original.id)


def test_resource_availability_qml_uses_authoritative_detail_contract() -> None:
    root = Path("src/ui_qml/modules/project_management/qml/workspaces/resources")
    panel = (root / "panels/ResourcesDetailPanel.qml").read_text(encoding="utf-8")
    section = (root / "sections/ResourcesAvailabilitySection.qml").read_text(
        encoding="utf-8"
    )
    qmldir = (root / "sections/qmldir").read_text(encoding="utf-8")

    assert "ResourcesAvailabilitySection" in panel
    assert "authoritative calendar and workload projection is delivered" not in panel
    assert "ResourcesAvailabilitySection 1.0" in qmldir
    assert "loadResourceAvailability" in section
    assert 'sortingMode: "none"' in section
    assert "AppControls.DateField" in section
    assert "plannedCommitmentHours" in section
    assert "calendarSourceLabel" in section
    assert "ResourceAvailabilityService" not in section

