"""`ActivityService.list_recent_page_for_organization` -- a full, paginated
+ searchable Activity workspace read for a specific organization, used by
Organization Detail's Activity tab. Unlike Sites/Departments/Employees/
Documents, Activity was ALREADY correctly scoped to an explicit
organization_id before this change (`list_recent_for_organization_id`) --
this addition is about pagination/search, not fixing a session-active-org
bug."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.core.platform.common.exceptions import BusinessRuleError


def test_viewing_a_non_active_organization_returns_its_own_activity_correctly(services) -> None:
    organization_service = services["organization_service"]
    site_service = services["site_service"]
    activity_service = services["activity_service"]
    tenant_context_service = services["tenant_context_service"]

    org_a = organization_service.create_organization(
        organization_code="ACT-ORG-A", display_name="Activity Org A", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org_a.id)
    site_service.create_site(site_code="ACT-A-SITE", name="Activity A Site")

    org_b = organization_service.create_organization(
        organization_code="ACT-ORG-B", display_name="Activity Org B", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org_b.id)
    site_service.create_site(site_code="ACT-B-SITE", name="Activity B Site")

    # Session-active org is now B; ask for A's activity anyway.
    page = activity_service.list_recent_page_for_organization(org_a.id, page=1, page_size=25)
    messages = [entry.human_message for entry in page.items]
    assert any("Activity A Site" in m for m in messages)
    assert not any("Activity B Site" in m for m in messages)
    for entry in page.items:
        assert entry.organization_id == org_a.id


def test_no_leakage_from_the_active_organization_into_the_viewed_organization(services) -> None:
    organization_service = services["organization_service"]
    site_service = services["site_service"]
    activity_service = services["activity_service"]
    tenant_context_service = services["tenant_context_service"]

    org_a = organization_service.create_organization(
        organization_code="ACT-LEAK-A", display_name="Leak A", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org_a.id)
    site_service.create_site(site_code="LEAK-A-SITE", name="Leak A Site")

    org_b = organization_service.create_organization(
        organization_code="ACT-LEAK-B", display_name="Leak B", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org_b.id)
    site_service.create_site(site_code="LEAK-B-SITE", name="Leak B Site")

    page = activity_service.list_recent_page_for_organization(org_b.id, page=1, page_size=25)
    messages = [entry.human_message for entry in page.items]
    assert any("Leak B Site" in m for m in messages)
    assert not any("Leak A Site" in m for m in messages)


def test_cross_tenant_organization_id_is_rejected(services) -> None:
    activity_service = services["activity_service"]

    with pytest.raises(BusinessRuleError):
        # A tenant_id mismatch (simulated by asking the underlying scoped
        # method to view an org while forcing a foreign tenant_id) is
        # rejected -- the repository's tenant boundary, exercised the same
        # way list_recent's existing coverage already proves for the
        # unpaginated method.
        activity_service._activity_repo.list_page_recent(
            page=1,
            page_size=25,
            tenant_id="foreign-tenant-activity-xyz",
            organization_id="whatever-org",
        )


def test_inactive_and_archived_organizations_still_have_readable_activity_history(services) -> None:
    organization_service = services["organization_service"]
    site_service = services["site_service"]
    activity_service = services["activity_service"]
    tenant_context_service = services["tenant_context_service"]

    org = organization_service.create_organization(
        organization_code="ACT-HIST", display_name="History Org", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org.id)
    site_service.create_site(site_code="HIST-SITE", name="History Site")

    other = organization_service.create_organization(
        organization_code="ACT-HIST-OTHER", display_name="History Other", timezone_name="UTC", base_currency="USD"
    )
    organization_service.deactivate_organization(org.id)
    tenant_context_service.set_active_organization(other.id)

    page = activity_service.list_recent_page_for_organization(org.id, page=1, page_size=25)
    assert any("History Site" in entry.human_message for entry in page.items)

    organization_service.archive_organization(org.id)
    page = activity_service.list_recent_page_for_organization(org.id, page=1, page_size=25)
    assert any("History Site" in entry.human_message for entry in page.items)


def test_search_filters_server_side_by_human_message(services) -> None:
    organization_service = services["organization_service"]
    site_service = services["site_service"]
    department_service = services["department_service"]
    activity_service = services["activity_service"]
    tenant_context_service = services["tenant_context_service"]

    org = organization_service.create_organization(
        organization_code="ACT-SEARCH", display_name="Search Org", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org.id)
    site_service.create_site(site_code="SEARCH-SITE", name="Findable Site")
    department_service.create_department(department_code="SEARCH-DEPT", name="Other Department")

    page = activity_service.list_recent_page_for_organization(
        org.id, page=1, page_size=25, search="Findable"
    )
    assert len(page.items) == 1
    assert "Findable Site" in page.items[0].human_message
    assert page.filtered_total == 1
    assert page.total >= 2


def test_since_cutoff_excludes_older_entries(services) -> None:
    organization_service = services["organization_service"]
    site_service = services["site_service"]
    activity_service = services["activity_service"]
    tenant_context_service = services["tenant_context_service"]

    org = organization_service.create_organization(
        organization_code="ACT-SINCE", display_name="Since Org", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org.id)
    site_service.create_site(site_code="SINCE-SITE", name="Since Site")

    future_cutoff = datetime.now(timezone.utc) + timedelta(days=1)
    page = activity_service.list_recent_page_for_organization(
        org.id, page=1, page_size=25, since=future_cutoff
    )
    assert page.items == []
    assert page.filtered_total == 0
    assert page.total >= 1
