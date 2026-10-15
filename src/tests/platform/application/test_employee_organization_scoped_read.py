"""`EmployeeQueryHandler.list_employees_page_for_organization` -- a tenant-scoped
(not active-organization-scoped) paginated read, added for Organization
Detail's Employees tab so an admin can view ANY organization's employees
regardless of which organization is currently active in their own session.

Read-only: create/update/delete continue using the caller's active
organization unchanged (see test_employee_platform_foundation.py)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.core.platform.application.master_data.department.dto.commands.department import (
    DepartmentCreateCommand,
)
from src.core.platform.application.master_data.employee.dto.commands.employee import (
    EmployeeCreateCommand,
)
from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.domain.master_data.employee import EmployeeLifecycleStatus
from src.core.platform.infrastructure.persistence.orm.master_data.department.departments import (
    DepartmentORM,
)
from src.core.platform.infrastructure.persistence.orm.master_data.employee.employee import (
    EmployeeORM,
)
from src.core.platform.infrastructure.persistence.orm.master_data.org.org import (
    OrganizationORM,
)
from src.core.platform.infrastructure.persistence.orm.tenant.tenancy.tenant import (
    TenantORM,
)


def test_viewing_a_non_active_organization_returns_its_own_employees_correctly(services) -> None:
    tenant_context_service = services["tenant_context_service"]

    org_a = services["organization_commands"].create_organization(
        organization_code="ORG-A", display_name="Org A", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org_a.id)
    dept_a = services["department_commands"].create_department(DepartmentCreateCommand(department_code="ORG-A-DEPT", name="Org A Dept"))
    services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="A-EMP-1", full_name="A Employee One", department_id=dept_a.id))
    services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="A-EMP-2", full_name="A Employee Two", department_id=dept_a.id))

    org_b = services["organization_commands"].create_organization(
        organization_code="ORG-B", display_name="Org B", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org_b.id)
    dept_b = services["department_commands"].create_department(DepartmentCreateCommand(department_code="ORG-B-DEPT", name="Org B Dept"))
    services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="B-EMP-1", full_name="B Employee One", department_id=dept_b.id))

    # Session-active org is now B; ask for A's employees anyway.
    page = services["employee_query"].list_employees_page_for_organization(org_a.id, page=1, page_size=25)

    names = sorted(employee.full_name for employee in page.items)
    assert names == ["A Employee One", "A Employee Two"]
    assert page.total == 2
    assert page.filtered_total == 2
    for employee in page.items:
        assert employee.organization_id == org_a.id


def test_no_leakage_from_the_active_organization_into_the_viewed_organization(services) -> None:
    tenant_context_service = services["tenant_context_service"]

    org_a = services["organization_commands"].create_organization(
        organization_code="LEAK-A", display_name="Leak A", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org_a.id)
    dept_a = services["department_commands"].create_department(DepartmentCreateCommand(department_code="LEAK-A-DEPT", name="Leak A Dept"))
    services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="LEAK-A-1", full_name="Leak A Employee", department_id=dept_a.id))

    org_b = services["organization_commands"].create_organization(
        organization_code="LEAK-B", display_name="Leak B", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org_b.id)
    dept_b = services["department_commands"].create_department(DepartmentCreateCommand(department_code="LEAK-B-DEPT", name="Leak B Dept"))
    services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="LEAK-B-1", full_name="Leak B Employee", department_id=dept_b.id))

    # Still active in B; explicitly ask for B's own employees -- must not
    # also include anything from A, proving the query is genuinely
    # org-filtered and not accidentally returning the whole tenant.
    page = services["employee_query"].list_employees_page_for_organization(org_b.id, page=1, page_size=25)
    names = {employee.full_name for employee in page.items}
    assert names == {"Leak B Employee"}
    assert "Leak A Employee" not in names


def test_cross_tenant_organization_id_is_rejected_not_visible(services) -> None:
    session = services["session"]
    tenant_context_service = services["tenant_context_service"]
    caller_tenant_id = tenant_context_service.require_active_tenant_id(operation_label="test setup")

    foreign_tenant_id = "foreign-tenant-emp-xyz"
    foreign_org_id = "foreign-org-emp-xyz"
    session.add(
        TenantORM(
            id=foreign_tenant_id,
            tenant_code="FOREIGN-TENANT-EMP",
            display_name="Foreign Tenant",
            version=1,
        )
    )
    session.commit()
    session.add(
        OrganizationORM(
            id=foreign_org_id,
            tenant_id=foreign_tenant_id,
            organization_code="FOREIGN-EMP",
            display_name="Foreign Org",
            timezone_name="UTC",
            base_currency="USD",
            status="active",
            version=1,
        )
    )
    session.commit()
    now = datetime.now(UTC)
    session.add(
        DepartmentORM(
            id="foreign-department-1",
            tenant_id=foreign_tenant_id,
            organization_id=foreign_org_id,
            department_code="FOREIGN-EMP-DEPT",
            name="Foreign Department",
            is_active=True,
            created_at=now,
            updated_at=now,
            version=1,
        )
    )
    session.commit()
    session.add(
        EmployeeORM(
            id="foreign-employee-1",
            tenant_id=foreign_tenant_id,
            organization_id=foreign_org_id,
            department_id="foreign-department-1",
            employee_code="FOREIGN-EMP-1",
            full_name="Foreign Employee",
            status=EmployeeLifecycleStatus.ACTIVE,
            version=1,
        )
    )
    session.commit()

    assert foreign_tenant_id != caller_tenant_id
    with pytest.raises(NotFoundError):
        services["employee_query"].list_employees_page_for_organization(foreign_org_id, page=1, page_size=25)


def test_inactive_and_archived_organizations_still_have_readable_employee_history(services) -> None:
    tenant_context_service = services["tenant_context_service"]

    org = services["organization_commands"].create_organization(
        organization_code="HIST-EMP", display_name="History Org", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org.id)
    dept = services["department_commands"].create_department(DepartmentCreateCommand(department_code="HIST-EMP-DEPT", name="History Dept"))
    services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="HIST-EMP-1", full_name="History Employee", department_id=dept.id))

    other = services["organization_commands"].create_organization(
        organization_code="HIST-EMP-OTHER", display_name="History Other", timezone_name="UTC", base_currency="USD"
    )
    services["organization_lifecycle"].deactivate_organization(org.id)
    tenant_context_service.set_active_organization(other.id)

    page = services["employee_query"].list_employees_page_for_organization(org.id, page=1, page_size=25)
    assert [employee.full_name for employee in page.items] == ["History Employee"]

    services["organization_lifecycle"].archive_organization(org.id)
    page = services["employee_query"].list_employees_page_for_organization(org.id, page=1, page_size=25)
    assert [employee.full_name for employee in page.items] == ["History Employee"]


def test_mutation_paths_still_use_the_active_organization_not_the_viewed_one(services) -> None:
    """create_employee()/update_employee() are unaffected by this read-only
    addition -- they keep using the caller's active organization, the
    existing, unchanged domain rule (do not weaken mutation scoping)."""
    tenant_context_service = services["tenant_context_service"]

    org_a = services["organization_commands"].create_organization(
        organization_code="MUT-EMP-A", display_name="Mutation A", timezone_name="UTC", base_currency="USD"
    )
    org_b = services["organization_commands"].create_organization(
        organization_code="MUT-EMP-B", display_name="Mutation B", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org_b.id)
    dept_b = services["department_commands"].create_department(DepartmentCreateCommand(department_code="MUT-EMP-DEPT", name="Mutation Dept"))

    created = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="MUT-EMP", full_name="Mutation Employee", department_id=dept_b.id))
    assert created.organization_id == org_b.id

    page_a = services["employee_query"].list_employees_page_for_organization(org_a.id, page=1, page_size=25)
    assert page_a.items == []
    page_b = services["employee_query"].list_employees_page_for_organization(org_b.id, page=1, page_size=25)
    assert [e.full_name for e in page_b.items] == ["Mutation Employee"]
