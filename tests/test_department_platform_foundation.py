from __future__ import annotations

from core.platform.common.exceptions import ValidationError


def test_department_service_scopes_department_master_data_by_active_organization(services):
    organization_service = services["organization_service"]
    department_service = services["department_service"]
    site_service = services["site_service"]

    default_organization = organization_service.get_active_organization()
    site = site_service.create_site(site_code="HQ", name="Headquarters")
    created = department_service.create_department(
        department_code="OPS",
        name="Operations",
        site_id=site.id,
        department_type="OPERATIONS",
        cost_center_code="CC-100",
    )

    assert created.organization_id == default_organization.id
    assert created.site_id == site.id
    assert created.department_type == "OPERATIONS"
    assert created.cost_center_code == "CC-100"
    assert created.created_at is not None
    assert created.updated_at is not None
    assert [department.name for department in department_service.list_departments()] == ["Operations"]

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

    department_service.create_department(department_code="OPS", name="Operations")

    try:
        department_service.create_department(department_code="OPS", name="Second Operations")
    except ValidationError as exc:
        assert exc.code == "DEPARTMENT_CODE_EXISTS"
    else:
        raise AssertionError("Expected duplicate department code validation error.")


def test_department_service_updates_department_metadata(services):
    department_service = services["department_service"]
    site_service = services["site_service"]
    site = site_service.create_site(site_code="PLANT1", name="Plant 1")
    created = department_service.create_department(department_code="QA", name="Quality")

    updated = department_service.update_department(
        created.id,
        name="Quality Assurance",
        site_id=site.id,
        department_type="QUALITY",
        cost_center_code="QA-200",
        is_active=False,
        expected_version=created.version,
    )

    assert updated.name == "Quality Assurance"
    assert updated.site_id == site.id
    assert updated.department_type == "QUALITY"
    assert updated.cost_center_code == "QA-200"
    assert updated.is_active is False
    assert [department.name for department in department_service.list_departments(active_only=False)] == [
        "Quality Assurance"
    ]


def test_department_service_can_reference_maintenance_default_location(services):
    department_service = services["department_service"]
    site = services["site_service"].create_site(site_code="MNT-HQ", name="Maintenance HQ")
    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="ops-yard",
        name="Ops Yard",
    )

    created = department_service.create_department(
        department_code="MNT",
        name="Maintenance",
        site_id=site.id,
        default_location_id=location.id,
    )
    updated = department_service.update_department(
        created.id,
        name="Maintenance Team",
        expected_version=created.version,
    )

    assert created.default_location_id == location.id
    assert updated.default_location_id == location.id
    assert [row.id for row in department_service.list_available_location_references(site_id=site.id)] == [location.id]


def test_department_service_rejects_default_location_from_other_site(services):
    department_service = services["department_service"]
    site_a = services["site_service"].create_site(site_code="DEPT-A", name="Dept Site A")
    site_b = services["site_service"].create_site(site_code="DEPT-B", name="Dept Site B")
    location = services["maintenance_location_service"].create_location(
        site_id=site_a.id,
        location_code="remote-yard",
        name="Remote Yard",
    )

    try:
        department_service.create_department(
            department_code="OPS",
            name="Operations",
            site_id=site_b.id,
            default_location_id=location.id,
        )
    except ValidationError as exc:
        assert exc.code == "DEPARTMENT_LOCATION_SITE_INVALID"
    else:
        raise AssertionError("Expected department default-location site validation error.")
