"""`SiteService.list_sites_page_for_organization` -- a tenant-scoped (not
active-organization-scoped) paginated read, added for Organization Detail's
Sites tab so an admin can view ANY organization's sites regardless of which
organization is currently active in their own session.

Read-only: create/update/delete continue using the caller's active
organization unchanged (see test_site_platform_foundation.py)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.infrastructure.persistence.orm.master_data.org.org import (
    OrganizationORM,
)
from src.core.platform.infrastructure.persistence.orm.master_data.site.sites import (
    SiteORM,
)
from src.core.platform.infrastructure.persistence.orm.tenant.tenancy.tenant import (
    TenantORM,
)


def test_viewing_a_non_active_organization_returns_its_own_sites_correctly(services) -> None:
    organization_service = services["organization_service"]
    site_service = services["site_service"]
    tenant_context_service = services["tenant_context_service"]

    org_a = organization_service.create_organization(
        organization_code="ORG-A", display_name="Org A", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org_a.id)
    site_service.create_site(site_code="A-SITE-1", name="A Site One", city="Lagos", country="Nigeria")
    site_service.create_site(site_code="A-SITE-2", name="A Site Two", city="Abuja", country="Nigeria")

    org_b = organization_service.create_organization(
        organization_code="ORG-B", display_name="Org B", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org_b.id)
    site_service.create_site(site_code="B-SITE-1", name="B Site One", city="Douala", country="Cameroon")

    # Session-active org is now B; ask for A's sites anyway.
    page = site_service.list_sites_page_for_organization(org_a.id, page=1, page_size=25)

    names = sorted(site.name for site in page.items)
    assert names == ["A Site One", "A Site Two"]
    assert page.total == 2
    assert page.filtered_total == 2
    for site in page.items:
        assert site.organization_id == org_a.id


def test_no_leakage_from_the_active_organization_into_the_viewed_organization(services) -> None:
    organization_service = services["organization_service"]
    site_service = services["site_service"]
    tenant_context_service = services["tenant_context_service"]

    org_a = organization_service.create_organization(
        organization_code="LEAK-A", display_name="Leak A", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org_a.id)
    site_service.create_site(site_code="LEAK-A-1", name="Leak A Site")

    org_b = organization_service.create_organization(
        organization_code="LEAK-B", display_name="Leak B", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org_b.id)
    site_service.create_site(site_code="LEAK-B-1", name="Leak B Site")

    # Still active in B; explicitly ask for B's own sites -- must not also
    # include anything from A, proving the query is genuinely org-filtered
    # and not accidentally returning the whole tenant.
    page = site_service.list_sites_page_for_organization(org_b.id, page=1, page_size=25)
    names = {site.name for site in page.items}
    assert names == {"Leak B Site"}
    assert "Leak A Site" not in names


def test_cross_tenant_organization_id_is_rejected_not_visible(services) -> None:
    session = services["session"]
    site_service = services["site_service"]
    tenant_context_service = services["tenant_context_service"]
    caller_tenant_id = tenant_context_service.require_active_tenant_id(operation_label="test setup")

    foreign_tenant_id = "foreign-tenant-xyz"
    foreign_org_id = "foreign-org-xyz"
    now = datetime.now(timezone.utc)
    session.add(
        TenantORM(
            id=foreign_tenant_id,
            tenant_code="FOREIGN-TENANT",
            display_name="Foreign Tenant",
            version=1,
        )
    )
    session.commit()
    session.add(
        OrganizationORM(
            id=foreign_org_id,
            tenant_id=foreign_tenant_id,
            organization_code="FOREIGN",
            display_name="Foreign Org",
            timezone_name="UTC",
            base_currency="USD",
            status="active",
            version=1,
        )
    )
    session.add(
        SiteORM(
            id="foreign-site-1",
            tenant_id=foreign_tenant_id,
            organization_id=foreign_org_id,
            site_code="FOREIGN-SITE",
            name="Foreign Site",
            status="active",
            created_at=now,
            updated_at=now,
            version=1,
        )
    )
    session.commit()

    assert foreign_tenant_id != caller_tenant_id
    with pytest.raises(NotFoundError):
        site_service.list_sites_page_for_organization(foreign_org_id, page=1, page_size=25)


def test_inactive_and_archived_organizations_still_have_readable_site_history(services) -> None:
    organization_service = services["organization_service"]
    site_service = services["site_service"]
    tenant_context_service = services["tenant_context_service"]

    org = organization_service.create_organization(
        organization_code="HIST", display_name="History Org", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org.id)
    site_service.create_site(site_code="HIST-SITE", name="History Site")

    # Deactivating/archiving the ORGANIZATION clears it as the active
    # context (Organization lifecycle) -- switch back to some other active
    # org first, exactly like an admin browsing Organization Detail would.
    other = organization_service.create_organization(
        organization_code="HIST-OTHER", display_name="History Other", timezone_name="UTC", base_currency="USD"
    )
    organization_service.deactivate_organization(org.id)
    tenant_context_service.set_active_organization(other.id)

    page = site_service.list_sites_page_for_organization(org.id, page=1, page_size=25)
    assert [site.name for site in page.items] == ["History Site"]

    organization_service.archive_organization(org.id)
    page = site_service.list_sites_page_for_organization(org.id, page=1, page_size=25)
    assert [site.name for site in page.items] == ["History Site"]


def test_mutation_paths_still_use_the_active_organization_not_the_viewed_one(services) -> None:
    """create_site()/update_site() are unaffected by this read-only addition
    -- they keep using the caller's active organization, the existing,
    unchanged domain rule (see requirement: do not weaken mutation scoping)."""
    organization_service = services["organization_service"]
    site_service = services["site_service"]
    tenant_context_service = services["tenant_context_service"]

    org_a = organization_service.create_organization(
        organization_code="MUT-A", display_name="Mutation A", timezone_name="UTC", base_currency="USD"
    )
    org_b = organization_service.create_organization(
        organization_code="MUT-B", display_name="Mutation B", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org_b.id)

    # Even though nothing here "views" org A, creating a site always lands
    # in the active organization (B), never anywhere implied by a read call.
    created = site_service.create_site(site_code="MUT-SITE", name="Mutation Site")
    assert created.organization_id == org_b.id

    page_a = site_service.list_sites_page_for_organization(org_a.id, page=1, page_size=25)
    assert page_a.items == []
    page_b = site_service.list_sites_page_for_organization(org_b.id, page=1, page_size=25)
    assert [s.name for s in page_b.items] == ["Mutation Site"]
