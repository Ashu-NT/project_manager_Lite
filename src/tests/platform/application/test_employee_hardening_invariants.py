"""Regression coverage for the Employee Enterprise HR Backbone hardening
pass: Organization/Department/Site integrity, Employee Code uniqueness
scoping, Employee<->User one-to-one linking, and the explicit
activate/deactivate lifecycle. Mirrors the coverage style already
established for Department in test_department_lifecycle_hierarchy_hod_
hardening.py."""

from __future__ import annotations

import pytest

from src.core.platform.common.exceptions import ValidationError


# ---------------------------------------------------------------------------
# Organization must match Department
# ---------------------------------------------------------------------------


def test_department_must_belong_to_employees_active_organization(services) -> None:
    employee_service = services["employee_service"]
    department_service = services["department_service"]
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]

    default_organization = tenant_context_service.get_active_organization()

    other_org = organization_service.create_organization(
        organization_code="EHI-ORG-B", display_name="Org B", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(other_org.id)
    foreign_department = department_service.create_department(department_code="EHI-D-B", name="Dept In Org B")

    tenant_context_service.set_active_organization(default_organization.id)
    with pytest.raises(ValidationError) as exc_info:
        employee_service.create_employee(
            employee_code="EHI-E-CROSSORG", full_name="Cross Org", department_id=foreign_department.id
        )
    assert exc_info.value.code == "EMPLOYEE_DEPARTMENT_INVALID"


# ---------------------------------------------------------------------------
# Site/Department invariant
# ---------------------------------------------------------------------------


def test_employee_site_derives_from_department_site_when_not_given(services) -> None:
    employee_service = services["employee_service"]
    department_service = services["department_service"]
    site_service = services["site_service"]

    site = site_service.create_site(site_code="EHI-SITE-1", name="HQ")
    department = department_service.create_department(
        department_code="EHI-D1", name="Dept With Site", site_id=site.id
    )

    employee = employee_service.create_employee(
        employee_code="EHI-E1", full_name="Employee One", department_id=department.id
    )

    assert employee.site_id == site.id


def test_employee_site_explicit_override_contradicting_department_site_is_rejected(services) -> None:
    employee_service = services["employee_service"]
    department_service = services["department_service"]
    site_service = services["site_service"]

    site_a = site_service.create_site(site_code="EHI-SITE-A", name="Site A")
    site_b = site_service.create_site(site_code="EHI-SITE-B", name="Site B")
    department = department_service.create_department(
        department_code="EHI-D2", name="Dept With Site A", site_id=site_a.id
    )

    with pytest.raises(ValidationError) as exc_info:
        employee_service.create_employee(
            employee_code="EHI-E2",
            full_name="Employee Two",
            department_id=department.id,
            site_id=site_b.id,
        )
    assert exc_info.value.code == "EMPLOYEE_SITE_DEPARTMENT_MISMATCH"


def test_employee_may_have_any_site_when_department_is_organization_wide(services) -> None:
    employee_service = services["employee_service"]
    department_service = services["department_service"]
    site_service = services["site_service"]

    site = site_service.create_site(site_code="EHI-SITE-2", name="Any Site")
    department = department_service.create_department(department_code="EHI-D3", name="Org Wide Dept")

    employee = employee_service.create_employee(
        employee_code="EHI-E3", full_name="Employee Three", department_id=department.id, site_id=site.id
    )
    assert employee.site_id == site.id

    employee_no_site = employee_service.create_employee(
        employee_code="EHI-E3B", full_name="Employee Three B", department_id=department.id
    )
    assert employee_no_site.site_id is None


# ---------------------------------------------------------------------------
# Department transfer site resolution
# ---------------------------------------------------------------------------


def test_department_transfer_to_site_bound_department_resolves_site_in_same_operation(services) -> None:
    employee_service = services["employee_service"]
    department_service = services["department_service"]
    site_service = services["site_service"]

    site = site_service.create_site(site_code="EHI-SITE-3", name="Target Site")
    origin_department = department_service.create_department(department_code="EHI-D4", name="Origin Dept")
    target_department = department_service.create_department(
        department_code="EHI-D5", name="Target Dept", site_id=site.id
    )
    employee = employee_service.create_employee(
        employee_code="EHI-E4", full_name="Employee Four", department_id=origin_department.id
    )
    assert employee.site_id is None

    updated = employee_service.update_employee(employee.id, department_id=target_department.id)

    assert updated.department_id == target_department.id
    assert updated.site_id == site.id


def test_department_transfer_to_organization_wide_department_preserves_existing_site(services) -> None:
    employee_service = services["employee_service"]
    department_service = services["department_service"]
    site_service = services["site_service"]

    origin_site = site_service.create_site(site_code="EHI-SITE-4", name="Origin Site")
    origin_department = department_service.create_department(
        department_code="EHI-D6", name="Origin Dept With Site", site_id=origin_site.id
    )
    target_department = department_service.create_department(department_code="EHI-D7", name="Org Wide Target")
    employee = employee_service.create_employee(
        employee_code="EHI-E5", full_name="Employee Five", department_id=origin_department.id
    )
    assert employee.site_id == origin_site.id

    updated = employee_service.update_employee(employee.id, department_id=target_department.id)

    assert updated.department_id == target_department.id
    assert updated.site_id == origin_site.id


# ---------------------------------------------------------------------------
# Employee Code uniqueness scoping
# ---------------------------------------------------------------------------


def test_employee_code_unique_within_organization_but_not_globally(services) -> None:
    employee_service = services["employee_service"]
    department_service = services["department_service"]
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]

    default_organization = tenant_context_service.get_active_organization()
    department = department_service.create_department(department_code="EHI-D8", name="Code Dept")
    employee_service.create_employee(
        employee_code="EHI-DUP-CODE", full_name="Employee In Org A", department_id=department.id
    )

    with pytest.raises(ValidationError) as exc_info:
        employee_service.create_employee(
            employee_code="EHI-DUP-CODE", full_name="Duplicate In Org A", department_id=department.id
        )
    assert exc_info.value.code == "EMPLOYEE_CODE_EXISTS"

    other_org = organization_service.create_organization(
        organization_code="EHI-ORG-C", display_name="Org C", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(other_org.id)
    other_department = department_service.create_department(department_code="EHI-D9", name="Code Dept Org C")
    other_org_employee = employee_service.create_employee(
        employee_code="EHI-DUP-CODE", full_name="Employee In Org C", department_id=other_department.id
    )
    assert other_org_employee.employee_code == "EHI-DUP-CODE"

    tenant_context_service.set_active_organization(default_organization.id)


# ---------------------------------------------------------------------------
# Employee<->User link validation
# ---------------------------------------------------------------------------


def test_link_employee_user_account_rejects_nonexistent_user(services) -> None:
    employee_service = services["employee_service"]
    department_service = services["department_service"]

    department = department_service.create_department(department_code="EHI-D10", name="Link Dept")
    employee = employee_service.create_employee(
        employee_code="EHI-E6", full_name="Employee Six", department_id=department.id
    )

    with pytest.raises(ValidationError) as exc_info:
        employee_service.link_employee_user_account(employee.id, "no-such-user-id")
    assert exc_info.value.code == "EMPLOYEE_USER_LINK_USER_NOT_FOUND"


def test_link_employee_user_account_succeeds_for_valid_human_user_and_can_be_unlinked(services) -> None:
    employee_service = services["employee_service"]
    department_service = services["department_service"]
    auth_service = services["auth_service"]

    department = department_service.create_department(department_code="EHI-D11", name="Link Dept Two")
    employee = employee_service.create_employee(
        employee_code="EHI-E7", full_name="Employee Seven", department_id=department.id
    )
    user = auth_service.onboard_tenant_user(
        username="ehi-link-user", raw_password="StrongPass123!", display_name="Link User"
    )

    linked = employee_service.link_employee_user_account(employee.id, user.id)
    assert linked.user_id == user.id

    unlinked = employee_service.unlink_employee_user_account(employee.id)
    assert unlinked.user_id is None


def test_link_employee_user_account_rejects_user_already_linked_to_another_employee(services) -> None:
    employee_service = services["employee_service"]
    department_service = services["department_service"]
    auth_service = services["auth_service"]

    department = department_service.create_department(department_code="EHI-D12", name="Link Dept Three")
    employee_one = employee_service.create_employee(
        employee_code="EHI-E8", full_name="Employee Eight", department_id=department.id
    )
    employee_two = employee_service.create_employee(
        employee_code="EHI-E9", full_name="Employee Nine", department_id=department.id
    )
    user = auth_service.onboard_tenant_user(
        username="ehi-double-link-user", raw_password="StrongPass123!", display_name="Double Link User"
    )
    employee_service.link_employee_user_account(employee_one.id, user.id)

    with pytest.raises(ValidationError) as exc_info:
        employee_service.link_employee_user_account(employee_two.id, user.id)
    assert exc_info.value.code == "EMPLOYEE_USER_LINK_ALREADY_LINKED"


def test_deactivated_user_account_may_remain_linked_to_employee(services) -> None:
    employee_service = services["employee_service"]
    department_service = services["department_service"]
    auth_service = services["auth_service"]

    department = department_service.create_department(department_code="EHI-D13", name="Link Dept Four")
    employee = employee_service.create_employee(
        employee_code="EHI-E10", full_name="Employee Ten", department_id=department.id
    )
    user = auth_service.onboard_tenant_user(
        username="ehi-inactive-user", raw_password="StrongPass123!", display_name="Inactive User"
    )
    employee_service.link_employee_user_account(employee.id, user.id)

    auth_service.set_user_active(user.id, is_active=False)

    reloaded = employee_service.get_employee(employee.id)
    assert reloaded.user_id == user.id


def test_deactivating_employee_does_not_touch_linked_user_account(services) -> None:
    employee_service = services["employee_service"]
    department_service = services["department_service"]
    auth_service = services["auth_service"]

    department = department_service.create_department(department_code="EHI-D14", name="Link Dept Five")
    employee = employee_service.create_employee(
        employee_code="EHI-E11", full_name="Employee Eleven", department_id=department.id
    )
    user = auth_service.onboard_tenant_user(
        username="ehi-still-active-user", raw_password="StrongPass123!", display_name="Still Active User"
    )
    employee_service.link_employee_user_account(employee.id, user.id)

    employee_service.deactivate_employee(employee.id)

    reloaded_employee = employee_service.get_employee(employee.id)
    assert reloaded_employee.is_active is False
    assert reloaded_employee.user_id == user.id
    reloaded_user = next(u for u in auth_service.list_users() if u.id == user.id)
    assert reloaded_user.is_active is True


# ---------------------------------------------------------------------------
# Lifecycle transitions
# ---------------------------------------------------------------------------


def test_deactivate_employee_twice_rejects_same_state_transition(services) -> None:
    employee_service = services["employee_service"]
    department_service = services["department_service"]

    department = department_service.create_department(department_code="EHI-D15", name="Lifecycle Dept")
    employee = employee_service.create_employee(
        employee_code="EHI-E12", full_name="Employee Twelve", department_id=department.id
    )
    employee_service.deactivate_employee(employee.id)

    with pytest.raises(ValidationError) as exc_info:
        employee_service.deactivate_employee(employee.id)
    assert exc_info.value.code == "EMPLOYEE_ALREADY_INACTIVE"


def test_activate_already_active_employee_rejects_same_state_transition(services) -> None:
    employee_service = services["employee_service"]
    department_service = services["department_service"]

    department = department_service.create_department(department_code="EHI-D16", name="Lifecycle Dept Two")
    employee = employee_service.create_employee(
        employee_code="EHI-E13", full_name="Employee Thirteen", department_id=department.id
    )

    with pytest.raises(ValidationError) as exc_info:
        employee_service.activate_employee(employee.id)
    assert exc_info.value.code == "EMPLOYEE_ALREADY_ACTIVE"
