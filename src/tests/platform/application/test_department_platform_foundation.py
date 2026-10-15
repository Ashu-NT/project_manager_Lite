from __future__ import annotations

from src.core.platform.application.master_data.department.dto.commands.department import (
    DepartmentCreateCommand,
    DepartmentUpdateCommand,
)
from src.core.platform.application.master_data.site.dto.commands.site import (
    SiteCreateCommand,
)
from src.core.platform.common.exceptions import ValidationError


def test_department_service_scopes_department_master_data_by_active_organization(services):

    default_organization = services["tenant_context_service"].get_active_organization()
    site = services["site_commands"].create_site(SiteCreateCommand(site_code="HQ", name="Headquarters"))
    created = services["department_commands"].create_department(DepartmentCreateCommand(department_code="OPS", name="Operations", site_id=site.id, department_type="OPERATIONS", cost_center_code="CC-100"))

    assert created.organization_id == default_organization.id
    assert created.site_id == site.id
    assert created.department_type == "OPERATIONS"
    assert created.cost_center_code == "CC-100"
    assert created.created_at is not None
    assert created.updated_at is not None
    assert [department.name for department in services["department_query"].list_departments()] == ["Operations"]

    second_organization = services["organization_commands"].create_organization(
        organization_code="NORTH",
        display_name="North Division",
        timezone_name="Europe/Berlin",
        base_currency="EUR",
    )
    services["tenant_context_service"].set_active_organization(second_organization.id)

    assert services["department_query"].get_context_organization().display_name == "North Division"
    assert services["department_query"].list_departments() == []

    workshop = services["department_commands"].create_department(DepartmentCreateCommand(department_code="ENG", name="Engineering"))
    assert workshop.organization_id == second_organization.id
    assert [department.department_code for department in services["department_query"].list_departments()] == ["ENG"]

    services["tenant_context_service"].set_active_organization(default_organization.id)
    assert services["department_query"].get_context_organization().display_name == "Default Organization"
    assert [department.department_code for department in services["department_query"].list_departments()] == ["OPS"]


def test_department_service_rejects_duplicate_codes_inside_one_organization(services):

    services["department_commands"].create_department(DepartmentCreateCommand(department_code="OPS", name="Operations"))

    try:
        services["department_commands"].create_department(DepartmentCreateCommand(department_code="OPS", name="Second Operations"))
    except ValidationError as exc:
        assert exc.code == "DEPARTMENT_CODE_EXISTS"
    else:
        raise AssertionError("Expected duplicate department code validation error.")


def test_department_service_updates_department_metadata(services):
    site = services["site_commands"].create_site(SiteCreateCommand(site_code="PLANT1", name="Plant 1"))
    created = services["department_commands"].create_department(DepartmentCreateCommand(department_code="QA", name="Quality"))

    updated = services["department_commands"].update_department(DepartmentUpdateCommand(department_id=created.id, name="Quality Assurance", site_id=site.id, department_type="QUALITY", cost_center_code="QA-200", expected_version=created.version))

    assert updated.name == "Quality Assurance"
    assert updated.site_id == site.id
    assert updated.department_type == "QUALITY"
    assert updated.cost_center_code == "QA-200"

    deactivated = services["department_commands"].deactivate_department(updated.id)
    assert deactivated.is_active is False
    assert [department.name for department in services["department_query"].list_departments(active_only=False)] == [
        "Quality Assurance"
    ]



