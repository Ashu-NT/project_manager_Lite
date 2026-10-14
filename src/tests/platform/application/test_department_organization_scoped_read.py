"""`DepartmentQueryHandler.list_departments_page_for_organization` -- a
tenant-scoped (not active-organization-scoped) paginated read, added for
Organization Detail's Departments tab so an admin can view ANY
organization's departments regardless of which organization is currently
active in their own session.

Read-only: create/update/delete continue using the caller's active
organization unchanged (see test_department_platform_foundation.py)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.core.platform.application.master_data.department.dto import (
    DepartmentCreateCommand,
)
from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.infrastructure.persistence.orm.master_data.department.departments import (
    DepartmentORM,
)
from src.core.platform.infrastructure.persistence.orm.master_data.org.org import (
    OrganizationORM,
)
from src.core.platform.infrastructure.persistence.orm.tenant.tenancy.tenant import (
    TenantORM,
)


def test_viewing_a_non_active_organization_returns_its_own_departments_correctly(services) -> None:
    tenant_context_service = services["tenant_context_service"]

    org_a = services["organization_commands"].create_organization(
        organization_code="ORG-A", display_name="Org A", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org_a.id)
    services["department_commands"].create_department(DepartmentCreateCommand(department_code="A-DEPT-1", name="A Dept One"))
    services["department_commands"].create_department(DepartmentCreateCommand(department_code="A-DEPT-2", name="A Dept Two"))

    org_b = services["organization_commands"].create_organization(
        organization_code="ORG-B", display_name="Org B", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org_b.id)
    services["department_commands"].create_department(DepartmentCreateCommand(department_code="B-DEPT-1", name="B Dept One"))

    # Session-active org is now B; ask for A's departments anyway.
    page = services["department_query"].list_departments_page_for_organization(org_a.id, page=1, page_size=25)

    names = sorted(department.name for department in page.items)
    assert names == ["A Dept One", "A Dept Two"]
    assert page.total == 2
    assert page.filtered_total == 2
    for department in page.items:
        assert department.organization_id == org_a.id


def test_no_leakage_from_the_active_organization_into_the_viewed_organization(services) -> None:
    tenant_context_service = services["tenant_context_service"]

    org_a = services["organization_commands"].create_organization(
        organization_code="LEAK-A", display_name="Leak A", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org_a.id)
    services["department_commands"].create_department(DepartmentCreateCommand(department_code="LEAK-A-1", name="Leak A Dept"))

    org_b = services["organization_commands"].create_organization(
        organization_code="LEAK-B", display_name="Leak B", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org_b.id)
    services["department_commands"].create_department(DepartmentCreateCommand(department_code="LEAK-B-1", name="Leak B Dept"))

    # Still active in B; explicitly ask for B's own departments -- must not
    # also include anything from A, proving the query is genuinely
    # org-filtered and not accidentally returning the whole tenant.
    page = services["department_query"].list_departments_page_for_organization(org_b.id, page=1, page_size=25)
    names = {department.name for department in page.items}
    assert names == {"Leak B Dept"}
    assert "Leak A Dept" not in names


def test_cross_tenant_organization_id_is_rejected_not_visible(services) -> None:
    session = services["session"]
    tenant_context_service = services["tenant_context_service"]
    caller_tenant_id = tenant_context_service.require_active_tenant_id(operation_label="test setup")

    foreign_tenant_id = "foreign-tenant-dept-xyz"
    foreign_org_id = "foreign-org-dept-xyz"
    now = datetime.now(UTC)
    session.add(
        TenantORM(
            id=foreign_tenant_id,
            tenant_code="FOREIGN-TENANT-DEPT",
            display_name="Foreign Tenant",
            version=1,
        )
    )
    session.commit()
    session.add(
        OrganizationORM(
            id=foreign_org_id,
            tenant_id=foreign_tenant_id,
            organization_code="FOREIGN-DEPT",
            display_name="Foreign Org",
            timezone_name="UTC",
            base_currency="USD",
            status="active",
            version=1,
        )
    )
    session.commit()
    session.add(
        DepartmentORM(
            id="foreign-department-1",
            tenant_id=foreign_tenant_id,
            organization_id=foreign_org_id,
            department_code="FOREIGN-DEPT",
            name="Foreign Department",
            is_active=True,
            created_at=now,
            updated_at=now,
            version=1,
        )
    )
    session.commit()

    assert foreign_tenant_id != caller_tenant_id
    with pytest.raises(NotFoundError):
        services["department_query"].list_departments_page_for_organization(foreign_org_id, page=1, page_size=25)


def test_inactive_and_archived_organizations_still_have_readable_department_history(services) -> None:
    tenant_context_service = services["tenant_context_service"]

    org = services["organization_commands"].create_organization(
        organization_code="HIST-DEPT", display_name="History Org", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org.id)
    services["department_commands"].create_department(DepartmentCreateCommand(department_code="HIST-DEPT-1", name="History Dept"))

    other = services["organization_commands"].create_organization(
        organization_code="HIST-DEPT-OTHER", display_name="History Other", timezone_name="UTC", base_currency="USD"
    )
    services["organization_lifecycle"].deactivate_organization(org.id)
    tenant_context_service.set_active_organization(other.id)

    page = services["department_query"].list_departments_page_for_organization(org.id, page=1, page_size=25)
    assert [department.name for department in page.items] == ["History Dept"]

    services["organization_lifecycle"].archive_organization(org.id)
    page = services["department_query"].list_departments_page_for_organization(org.id, page=1, page_size=25)
    assert [department.name for department in page.items] == ["History Dept"]


def test_mutation_paths_still_use_the_active_organization_not_the_viewed_one(services) -> None:
    """create_department()/update_department() are unaffected by this
    read-only addition -- they keep using the caller's active organization,
    the existing, unchanged domain rule (do not weaken mutation scoping)."""
    tenant_context_service = services["tenant_context_service"]

    org_a = services["organization_commands"].create_organization(
        organization_code="MUT-DEPT-A", display_name="Mutation A", timezone_name="UTC", base_currency="USD"
    )
    org_b = services["organization_commands"].create_organization(
        organization_code="MUT-DEPT-B", display_name="Mutation B", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org_b.id)

    created = services["department_commands"].create_department(DepartmentCreateCommand(department_code="MUT-DEPT", name="Mutation Dept"))
    assert created.organization_id == org_b.id

    page_a = services["department_query"].list_departments_page_for_organization(org_a.id, page=1, page_size=25)
    assert page_a.items == []
    page_b = services["department_query"].list_departments_page_for_organization(org_b.id, page=1, page_size=25)
    assert [d.name for d in page_b.items] == ["Mutation Dept"]
