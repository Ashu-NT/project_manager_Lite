from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from src.core.modules.project_management.domain.projects.project import Project, ProjectResource
from src.core.platform.common.exceptions import ValidationError


def test_project_dto_normalizes_and_validates_fields():
    project = Project.create(
        name="  Plant Upgrade  ",
        description="  Rollout scope  ",
        client_name="  ACME  ",
        client_contact="  lead@example.com  ",
        planned_budget="1500.5",
        currency=" eur ",
        organization_id="  org-1  ",
        site_id="  site-1  ",
    )

    assert project.name == "Plant Upgrade"
    assert project.description == "Rollout scope"
    assert project.client_name == "ACME"
    assert project.client_contact == "lead@example.com"
    assert project.planned_budget == pytest.approx(1500.5)
    assert project.currency == "EUR"
    assert project.organization_id == "org-1"
    assert project.site_id == "site-1"


def test_project_dto_rejects_empty_name():
    with pytest.raises(ValidationError) as exc:
        Project.create(name="  ")

    assert exc.value.code == "PROJECT_NAME_EMPTY"


def test_project_dto_rejects_invalid_date_range():
    with pytest.raises(ValidationError) as exc:
        Project.create(
            name="Date Check",
            start_date=date(2026, 7, 10),
            end_date=date(2026, 7, 9),
        )

    assert exc.value.code == "PROJECT_DATE_RANGE_INVALID"


def test_project_dtos_reject_invalid_financial_currencies():
    with pytest.raises(ValidationError) as exc_project:
        Project.create(name="Invalid Currency", currency="BGN")
    assert exc_project.value.code == "PROJECT_CURRENCY_INVALID"

    with pytest.raises(ValidationError) as exc_resource:
        ProjectResource.create(
            project_id="project-1",
            resource_id="resource-1",
            currency_code="ZZZ",
        )
    assert exc_resource.value.code == "PROJECT_RESOURCE_CURRENCY_INVALID"


def test_project_replace_validates_final_state():
    project = Project.create(
        name="Sequenced Move",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 5),
    )

    updated = replace(
        project,
        start_date=date(2026, 7, 10),
        end_date=date(2026, 7, 15),
    )

    assert updated.start_date == date(2026, 7, 10)
    assert updated.end_date == date(2026, 7, 15)


def test_project_resource_dto_validates_planned_hours():
    resource = ProjectResource.create(
        project_id="  project-1  ",
        resource_id="  resource-1  ",
        hourly_rate="95.0",
        currency_code=" usd ",
        planned_hours="12",
    )

    assert resource.project_id == "project-1"
    assert resource.resource_id == "resource-1"
    assert resource.hourly_rate == pytest.approx(95.0)
    assert resource.currency_code == "USD"
    assert resource.planned_hours == pytest.approx(12.0)

    with pytest.raises(ValidationError) as exc:
        ProjectResource.create(
            project_id="project-1",
            resource_id="resource-1",
            planned_hours=-1,
        )

    assert exc.value.code == "PROJECT_RESOURCE_PLANNED_HOURS_INVALID"


def test_project_service_updates_date_pair_with_final_state_validation(services):
    project_service = services["project_service"]
    project = project_service.create_project(
        "Service Date Move",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 5),
    )

    updated = project_service.update_project(
        project.id,
        expected_version=project.version,
        start_date=date(2026, 7, 10),
        end_date=date(2026, 7, 15),
    )

    assert updated.start_date == date(2026, 7, 10)
    assert updated.end_date == date(2026, 7, 15)
