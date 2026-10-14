"""Regression coverage for the Employee Enterprise HR Backbone hardening
pass: Organization/Department/Site integrity, Employee Code uniqueness
scoping, Employee<->User one-to-one linking, and the explicit
activate/deactivate lifecycle. Mirrors the coverage style already
established for Department in test_department_lifecycle_hierarchy_hod_
hardening.py."""

from __future__ import annotations

import pytest

from src.core.platform.application.master_data.department.dto import (
    DepartmentCreateCommand,
)
from src.core.platform.application.master_data.employee.dto import (
    EmployeeCreateCommand,
    EmployeeUpdateCommand,
)
from src.core.platform.application.master_data.site.dto import (
    SiteCreateCommand,
)
from src.core.platform.common.exceptions import ValidationError

# ---------------------------------------------------------------------------
# Organization must match Department
# ---------------------------------------------------------------------------


def test_department_must_belong_to_employees_active_organization(services) -> None:
    tenant_context_service = services["tenant_context_service"]

    default_organization = tenant_context_service.get_active_organization()

    other_org = services["organization_commands"].create_organization(
        organization_code="EHI-ORG-B", display_name="Org B", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(other_org.id)
    foreign_department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="EHI-D-B", name="Dept In Org B"))

    tenant_context_service.set_active_organization(default_organization.id)
    with pytest.raises(ValidationError) as exc_info:
        services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="EHI-E-CROSSORG", full_name="Cross Org", department_id=foreign_department.id))
    assert exc_info.value.code == "EMPLOYEE_DEPARTMENT_INVALID"


# ---------------------------------------------------------------------------
# Site/Department invariant
# ---------------------------------------------------------------------------


def test_employee_site_derives_from_department_site_when_not_given(services) -> None:

    site = services["site_commands"].create_site(SiteCreateCommand(site_code="EHI-SITE-1", name="HQ"))
    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="EHI-D1", name="Dept With Site", site_id=site.id))

    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="EHI-E1", full_name="Employee One", department_id=department.id))

    assert employee.site_id == site.id


def test_employee_site_explicit_override_contradicting_department_site_is_rejected(services) -> None:

    site_a = services["site_commands"].create_site(SiteCreateCommand(site_code="EHI-SITE-A", name="Site A"))
    site_b = services["site_commands"].create_site(SiteCreateCommand(site_code="EHI-SITE-B", name="Site B"))
    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="EHI-D2", name="Dept With Site A", site_id=site_a.id))

    with pytest.raises(ValidationError) as exc_info:
        services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="EHI-E2", full_name="Employee Two", department_id=department.id, site_id=site_b.id))
    assert exc_info.value.code == "EMPLOYEE_SITE_DEPARTMENT_MISMATCH"


def test_employee_may_have_any_site_when_department_is_organization_wide(services) -> None:

    site = services["site_commands"].create_site(SiteCreateCommand(site_code="EHI-SITE-2", name="Any Site"))
    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="EHI-D3", name="Org Wide Dept"))

    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="EHI-E3", full_name="Employee Three", department_id=department.id, site_id=site.id))
    assert employee.site_id == site.id

    employee_no_site = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="EHI-E3B", full_name="Employee Three B", department_id=department.id))
    assert employee_no_site.site_id is None


# ---------------------------------------------------------------------------
# Department transfer site resolution
# ---------------------------------------------------------------------------


def test_department_transfer_to_site_bound_department_resolves_site_in_same_operation(services) -> None:

    site = services["site_commands"].create_site(SiteCreateCommand(site_code="EHI-SITE-3", name="Target Site"))
    origin_department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="EHI-D4", name="Origin Dept"))
    target_department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="EHI-D5", name="Target Dept", site_id=site.id))
    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="EHI-E4", full_name="Employee Four", department_id=origin_department.id))
    assert employee.site_id is None

    updated = services["employee_commands"].update_employee(EmployeeUpdateCommand(employee_id=employee.id, department_id=target_department.id))

    assert updated.department_id == target_department.id
    assert updated.site_id == site.id


def test_department_transfer_to_organization_wide_department_preserves_existing_site(services) -> None:

    origin_site = services["site_commands"].create_site(SiteCreateCommand(site_code="EHI-SITE-4", name="Origin Site"))
    origin_department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="EHI-D6", name="Origin Dept With Site", site_id=origin_site.id))
    target_department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="EHI-D7", name="Org Wide Target"))
    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="EHI-E5", full_name="Employee Five", department_id=origin_department.id))
    assert employee.site_id == origin_site.id

    updated = services["employee_commands"].update_employee(EmployeeUpdateCommand(employee_id=employee.id, department_id=target_department.id))

    assert updated.department_id == target_department.id
    assert updated.site_id == origin_site.id


# ---------------------------------------------------------------------------
# Employee Code uniqueness scoping
# ---------------------------------------------------------------------------


def test_employee_code_unique_within_organization_but_not_globally(services) -> None:
    tenant_context_service = services["tenant_context_service"]

    default_organization = tenant_context_service.get_active_organization()
    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="EHI-D8", name="Code Dept"))
    services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="EHI-DUP-CODE", full_name="Employee In Org A", department_id=department.id))

    with pytest.raises(ValidationError) as exc_info:
        services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="EHI-DUP-CODE", full_name="Duplicate In Org A", department_id=department.id))
    assert exc_info.value.code == "EMPLOYEE_CODE_EXISTS"

    other_org = services["organization_commands"].create_organization(
        organization_code="EHI-ORG-C", display_name="Org C", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(other_org.id)
    other_department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="EHI-D9", name="Code Dept Org C"))
    other_org_employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="EHI-DUP-CODE", full_name="Employee In Org C", department_id=other_department.id))
    assert other_org_employee.employee_code == "EHI-DUP-CODE"

    tenant_context_service.set_active_organization(default_organization.id)


# ---------------------------------------------------------------------------
# Employee<->User link validation
# ---------------------------------------------------------------------------


def test_link_employee_user_account_rejects_nonexistent_user(services) -> None:

    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="EHI-D10", name="Link Dept"))
    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="EHI-E6", full_name="Employee Six", department_id=department.id))

    with pytest.raises(ValidationError) as exc_info:
        services["employee_commands"].link_employee_user_account(employee.id, "no-such-user-id")
    assert exc_info.value.code == "EMPLOYEE_USER_LINK_USER_NOT_FOUND"


def test_link_employee_user_account_succeeds_for_valid_human_user_and_can_be_unlinked(services) -> None:

    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="EHI-D11", name="Link Dept Two"))
    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="EHI-E7", full_name="Employee Seven", department_id=department.id))
    user = services["user_registration"].onboard_tenant_user(
        username="ehi-link-user", raw_password="StrongPass123!", display_name="Link User"
    )

    linked = services["employee_commands"].link_employee_user_account(employee.id, user.id)
    assert linked.user_id == user.id

    unlinked = services["employee_commands"].unlink_employee_user_account(employee.id)
    assert unlinked.user_id is None


def test_link_employee_user_account_rejects_user_already_linked_to_another_employee(services) -> None:

    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="EHI-D12", name="Link Dept Three"))
    employee_one = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="EHI-E8", full_name="Employee Eight", department_id=department.id))
    employee_two = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="EHI-E9", full_name="Employee Nine", department_id=department.id))
    user = services["user_registration"].onboard_tenant_user(
        username="ehi-double-link-user", raw_password="StrongPass123!", display_name="Double Link User"
    )
    services["employee_commands"].link_employee_user_account(employee_one.id, user.id)

    with pytest.raises(ValidationError) as exc_info:
        services["employee_commands"].link_employee_user_account(employee_two.id, user.id)
    assert exc_info.value.code == "EMPLOYEE_USER_LINK_ALREADY_LINKED"


def test_deactivated_user_account_may_remain_linked_to_employee(services) -> None:

    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="EHI-D13", name="Link Dept Four"))
    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="EHI-E10", full_name="Employee Ten", department_id=department.id))
    user = services["user_registration"].onboard_tenant_user(
        username="ehi-inactive-user", raw_password="StrongPass123!", display_name="Inactive User"
    )
    services["employee_commands"].link_employee_user_account(employee.id, user.id)

    services["user_administration_commands"].set_user_active(user.id, is_active=False)

    reloaded = services["employee_query"].get_employee(employee.id)
    assert reloaded.user_id == user.id


def test_deactivating_employee_does_not_touch_linked_user_account(services) -> None:

    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="EHI-D14", name="Link Dept Five"))
    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="EHI-E11", full_name="Employee Eleven", department_id=department.id))
    user = services["user_registration"].onboard_tenant_user(
        username="ehi-still-active-user", raw_password="StrongPass123!", display_name="Still Active User"
    )
    services["employee_commands"].link_employee_user_account(employee.id, user.id)

    services["employee_commands"].deactivate_employee(employee.id)

    reloaded_employee = services["employee_query"].get_employee(employee.id)
    assert reloaded_employee.is_active is False
    assert reloaded_employee.user_id == user.id
    reloaded_user = next(u for u in services["user_directory_query"].list_users() if u.id == user.id)
    assert reloaded_user.is_active is True


# ---------------------------------------------------------------------------
# Lifecycle transitions
# ---------------------------------------------------------------------------


def test_deactivate_employee_twice_rejects_same_state_transition(services) -> None:

    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="EHI-D15", name="Lifecycle Dept"))
    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="EHI-E12", full_name="Employee Twelve", department_id=department.id))
    services["employee_commands"].deactivate_employee(employee.id)

    with pytest.raises(ValidationError) as exc_info:
        services["employee_commands"].deactivate_employee(employee.id)
    assert exc_info.value.code == "EMPLOYEE_ALREADY_INACTIVE"


def test_activate_already_active_employee_rejects_same_state_transition(services) -> None:

    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="EHI-D16", name="Lifecycle Dept Two"))
    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="EHI-E13", full_name="Employee Thirteen", department_id=department.id))

    with pytest.raises(ValidationError) as exc_info:
        services["employee_commands"].activate_employee(employee.id)
    assert exc_info.value.code == "EMPLOYEE_ALREADY_ACTIVE"
