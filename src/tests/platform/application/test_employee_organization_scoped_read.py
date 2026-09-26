"""`EmployeeService.list_employees_page_for_organization` -- a tenant-scoped
(not active-organization-scoped) paginated read, added for Organization
Detail's Employees tab so an admin can view ANY organization's employees
regardless of which organization is currently active in their own session.

Read-only: create/update/delete continue using the caller's active
organization unchanged (see test_employee_platform_foundation.py)."""

from __future__ import annotations

import pytest

from src.core.platform.common.exceptions import NotFoundError
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
    organization_service = services["organization_service"]
    employee_service = services["employee_service"]
    tenant_context_service = services["tenant_context_service"]

    org_a = organization_service.create_organization(
        organization_code="ORG-A", display_name="Org A", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org_a.id)
    employee_service.create_employee(employee_code="A-EMP-1", full_name="A Employee One")
    employee_service.create_employee(employee_code="A-EMP-2", full_name="A Employee Two")

    org_b = organization_service.create_organization(
        organization_code="ORG-B", display_name="Org B", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org_b.id)
    employee_service.create_employee(employee_code="B-EMP-1", full_name="B Employee One")

    # Session-active org is now B; ask for A's employees anyway.
    page = employee_service.list_employees_page_for_organization(org_a.id, page=1, page_size=25)

    names = sorted(employee.full_name for employee in page.items)
    assert names == ["A Employee One", "A Employee Two"]
    assert page.total == 2
    assert page.filtered_total == 2
    for employee in page.items:
        assert employee.organization_id == org_a.id


def test_no_leakage_from_the_active_organization_into_the_viewed_organization(services) -> None:
    organization_service = services["organization_service"]
    employee_service = services["employee_service"]
    tenant_context_service = services["tenant_context_service"]

    org_a = organization_service.create_organization(
        organization_code="LEAK-A", display_name="Leak A", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org_a.id)
    employee_service.create_employee(employee_code="LEAK-A-1", full_name="Leak A Employee")

    org_b = organization_service.create_organization(
        organization_code="LEAK-B", display_name="Leak B", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org_b.id)
    employee_service.create_employee(employee_code="LEAK-B-1", full_name="Leak B Employee")

    # Still active in B; explicitly ask for B's own employees -- must not
    # also include anything from A, proving the query is genuinely
    # org-filtered and not accidentally returning the whole tenant.
    page = employee_service.list_employees_page_for_organization(org_b.id, page=1, page_size=25)
    names = {employee.full_name for employee in page.items}
    assert names == {"Leak B Employee"}
    assert "Leak A Employee" not in names


def test_cross_tenant_organization_id_is_rejected_not_visible(services) -> None:
    session = services["session"]
    employee_service = services["employee_service"]
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
    session.add(
        EmployeeORM(
            id="foreign-employee-1",
            tenant_id=foreign_tenant_id,
            organization_id=foreign_org_id,
            employee_code="FOREIGN-EMP-1",
            full_name="Foreign Employee",
            is_active=True,
            version=1,
        )
    )
    session.commit()

    assert foreign_tenant_id != caller_tenant_id
    with pytest.raises(NotFoundError):
        employee_service.list_employees_page_for_organization(foreign_org_id, page=1, page_size=25)


def test_inactive_and_archived_organizations_still_have_readable_employee_history(services) -> None:
    organization_service = services["organization_service"]
    employee_service = services["employee_service"]
    tenant_context_service = services["tenant_context_service"]

    org = organization_service.create_organization(
        organization_code="HIST-EMP", display_name="History Org", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org.id)
    employee_service.create_employee(employee_code="HIST-EMP-1", full_name="History Employee")

    other = organization_service.create_organization(
        organization_code="HIST-EMP-OTHER", display_name="History Other", timezone_name="UTC", base_currency="USD"
    )
    organization_service.deactivate_organization(org.id)
    tenant_context_service.set_active_organization(other.id)

    page = employee_service.list_employees_page_for_organization(org.id, page=1, page_size=25)
    assert [employee.full_name for employee in page.items] == ["History Employee"]

    organization_service.archive_organization(org.id)
    page = employee_service.list_employees_page_for_organization(org.id, page=1, page_size=25)
    assert [employee.full_name for employee in page.items] == ["History Employee"]


def test_mutation_paths_still_use_the_active_organization_not_the_viewed_one(services) -> None:
    """create_employee()/update_employee() are unaffected by this read-only
    addition -- they keep using the caller's active organization, the
    existing, unchanged domain rule (do not weaken mutation scoping)."""
    organization_service = services["organization_service"]
    employee_service = services["employee_service"]
    tenant_context_service = services["tenant_context_service"]

    org_a = organization_service.create_organization(
        organization_code="MUT-EMP-A", display_name="Mutation A", timezone_name="UTC", base_currency="USD"
    )
    org_b = organization_service.create_organization(
        organization_code="MUT-EMP-B", display_name="Mutation B", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org_b.id)

    created = employee_service.create_employee(employee_code="MUT-EMP", full_name="Mutation Employee")
    assert created.organization_id == org_b.id

    page_a = employee_service.list_employees_page_for_organization(org_a.id, page=1, page_size=25)
    assert page_a.items == []
    page_b = employee_service.list_employees_page_for_organization(org_b.id, page=1, page_size=25)
    assert [e.full_name for e in page_b.items] == ["Mutation Employee"]
