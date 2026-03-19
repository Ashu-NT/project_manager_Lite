from __future__ import annotations

from core.platform.common.exceptions import ValidationError


def test_department_service_scopes_department_master_data_by_active_organization(services):
    organization_service = services["organization_service"]
    department_service = services["department_service"]

    default_organization = organization_service.get_active_organization()
    created = department_service.create_department(department_code="OPS", display_name="Operations")

    assert created.organization_id == default_organization.id
    assert [department.display_name for department in department_service.list_departments()] == ["Operations"]

    second_organization = organization_service.create_organization(
        organization_code="NORTH",
        display_name="North Division",
        timezone_name="Europe/Berlin",
        base_currency="EUR",
        is_active=False,
    )
    organization_service.set_active_organization(second_organization.id)

    assert department_service.get_context_organization().display_name == "North Division"
    assert department_service.list_departments() == []

    workshop = department_service.create_department(department_code="ENG", display_name="Engineering")
    assert workshop.organization_id == second_organization.id
    assert [department.department_code for department in department_service.list_departments()] == ["ENG"]

    organization_service.set_active_organization(default_organization.id)
    assert department_service.get_context_organization().display_name == "Default Organization"
    assert [department.department_code for department in department_service.list_departments()] == ["OPS"]


def test_department_service_rejects_duplicate_codes_inside_one_organization(services):
    department_service = services["department_service"]

    department_service.create_department(department_code="OPS", display_name="Operations")

    try:
        department_service.create_department(department_code="OPS", display_name="Second Operations")
    except ValidationError as exc:
        assert exc.code == "DEPARTMENT_CODE_EXISTS"
    else:
        raise AssertionError("Expected duplicate department code validation error.")


def test_department_service_updates_department_metadata(services):
    department_service = services["department_service"]
    created = department_service.create_department(department_code="QA", display_name="Quality")

    updated = department_service.update_department(
        created.id,
        display_name="Quality Assurance",
        is_active=False,
        expected_version=created.version,
    )

    assert updated.display_name == "Quality Assurance"
    assert updated.is_active is False
    assert [department.display_name for department in department_service.list_departments(active_only=False)] == [
        "Quality Assurance"
    ]
