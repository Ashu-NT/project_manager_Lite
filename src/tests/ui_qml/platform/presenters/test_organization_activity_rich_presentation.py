"""Organization Detail's full Activity tab: proves the rich, human-readable
`ActivityItemViewModel` mapping (title/description/actor/subject/tone/icon,
activation state) end-to-end through Controller -> Presenter -> Desktop API
-> Service, not just that raw entries come back."""

from __future__ import annotations

from src.application.runtime import build_desktop_api_registry
from src.ui_qml.platform.context import PlatformWorkspaceCatalog


def _build_admin_workspace(services):
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    return catalog, catalog.adminWorkspace


def test_activity_page_has_human_readable_titles_actor_and_subject(services) -> None:
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    site_service = services["site_service"]
    _catalog, admin = _build_admin_workspace(services)

    org = organization_service.create_organization(
        organization_code="ACT-RICH", display_name="Rich Activity Org", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org.id)
    site = site_service.create_site(site_code="RICH-SITE", name="Rich Site")

    result = admin.organizationActivityPage(org.id, 1, 25, "", "", "")
    items = result["items"]
    assert len(items) >= 2  # organization.create + site.create

    site_item = next(item for item in items if item["title"] == "Site created")
    assert site_item["subjectDisplay"] == "Rich Site"
    # Entity-name lookup resolved via the tenant-scoped Sites read, not a
    # raw id or a parsed guess -- confirm no raw id leaked into any
    # user-facing label (activationState.entityId is the one intentional,
    # allowed exception: an opaque routing payload, never displayed).
    assert site.id not in site_item["title"]
    assert site.id not in site_item["subjectDisplay"]
    assert site.id not in (site_item["description"] or "")
    assert site.id not in site_item["actorDisplay"]
    assert site_item["tone"] == "success"
    assert site_item["iconKey"] == "site"
    assert site_item["activationState"] == {"entityType": "site", "entityId": site.id}
    # Admin authenticated via the "admin" account in the test fixture --
    # actor resolution must not fall back to a raw id or "Authorized user".
    assert site_item["actorDisplay"] not in ("", None)
    assert site_item["actorDisplay"] != "System"

    org_item = next(item for item in items if item["title"] == "Organization created")
    assert org_item["subjectDisplay"] == "Rich Activity Org"
    # Organization's own activity has no local Detail destination (we are
    # already viewing this organization) -- not clickable.
    assert org_item["activationState"] is None

    assert result["totalCount"] >= 2
    assert result["filteredTotal"] >= 2


def test_activity_page_lifecycle_titles_use_activated_deactivated_archived_vocabulary(services) -> None:
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    _catalog, admin = _build_admin_workspace(services)

    org = organization_service.create_organization(
        organization_code="ACT-LIFECYCLE", display_name="Lifecycle Activity Org", timezone_name="UTC", base_currency="USD"
    )
    other = organization_service.create_organization(
        organization_code="ACT-LIFECYCLE-OTHER", display_name="Lifecycle Other", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org.id)
    organization_service.deactivate_organization(org.id)
    # Deactivating the currently-ACTIVE organization clears active-org
    # context -- switch to some other active org first, exactly like an
    # admin browsing Organization Detail would (ActivityService's scope
    # check requires an active organization to exist in session, same as
    # every other read here).
    tenant_context_service.set_active_organization(other.id)

    result = admin.organizationActivityPage(org.id, 1, 25, "", "", "")
    titles = [item["title"] for item in result["items"]]
    assert "Organization deactivated" in titles
    # Never the old enabled/disabled vocabulary.
    assert not any("enabled" in t.lower() or "disabled" in t.lower() for t in titles)
    deactivated_item = next(item for item in result["items"] if item["title"] == "Organization deactivated")
    assert deactivated_item["tone"] == "warning"


def test_activity_page_empty_and_filtered_no_results_states_are_distinct(services) -> None:
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    _catalog, admin = _build_admin_workspace(services)

    org = organization_service.create_organization(
        organization_code="ACT-EMPTY", display_name="Empty Activity Org", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org.id)

    result = admin.organizationActivityPage(org.id, 1, 25, "DOES-NOT-EXIST-ANYWHERE", "", "")
    assert result["items"] == []
    assert result["filteredTotal"] == 0
    assert result["totalCount"] >= 1  # organization.create still exists, just filtered out
    assert "filters" in result["noResultsState"].lower()
