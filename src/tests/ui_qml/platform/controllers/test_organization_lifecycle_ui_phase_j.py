"""Phase J -- Organization workspace lifecycle UI: server-side status filtering,
presenter-owned StatusChip tone (never inferred from text in QML), bulk archive
routed through the canonical BulkActionBar action set, and profile commands
that carry no lifecycle field."""

from __future__ import annotations

import dataclasses

from src.application.runtime import build_desktop_api_registry
from src.core.platform.api.desktop.master_data.org.models.organization import (
    OrganizationProvisionCommand,
    OrganizationUpdateCommand,
)
from src.ui_qml.platform.context import PlatformWorkspaceCatalog


def _create_org(services, code: str, name: str) -> str:
    org_service = services["organization_service"]
    organization = org_service.create_organization(
        organization_code=code,
        display_name=name,
        timezone_name="UTC",
        base_currency="USD",
    )
    return organization.id


def _build_admin_workspace(services):
    # See test_organization_bulk_actions.py -- both the catalog wrapper and
    # its adminWorkspace sub-controller must stay referenced for the whole
    # test, or PySide6 tears down the underlying QObject tree.
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    return catalog, catalog.adminWorkspace


def _row_by_id(admin, organization_id: str) -> dict:
    for item in admin.organizations.get("items", []):
        if item.get("id") == organization_id:
            return item
    raise AssertionError(f"organization {organization_id!r} not found in current page")


def test_status_filter_is_applied_server_side(services, qapp) -> None:
    _catalog, admin = _build_admin_workspace(services)
    org_service = services["organization_service"]
    active_id = _create_org(services, "SF-ACTIVE", "Stays Active")
    inactive_id = _create_org(services, "SF-INACTIVE", "Goes Inactive")
    org_service.deactivate_organization(inactive_id)

    admin.setOrganizationStatusFilter("active")
    admin.refresh()
    active_ids = {item["id"] for item in admin.organizations["items"]}
    assert active_id in active_ids
    assert inactive_id not in active_ids

    admin.setOrganizationStatusFilter("inactive")
    admin.refresh()
    inactive_ids = {item["id"] for item in admin.organizations["items"]}
    assert inactive_id in inactive_ids
    assert active_id not in inactive_ids

    # Clearing the filter (the toolbar's "Clear filters" empty-state action)
    # must restore both -- proof the filter, not a stale cache, drove the
    # narrower results above.
    admin.setOrganizationStatusFilter("")
    admin.refresh()
    all_ids = {item["id"] for item in admin.organizations["items"]}
    assert {active_id, inactive_id} <= all_ids


def test_status_label_carries_explicit_presenter_owned_tone(services, qapp) -> None:
    _catalog, admin = _build_admin_workspace(services)
    org_service = services["organization_service"]
    active_id = _create_org(services, "TONE-ACT", "Tone Active")
    inactive_id = _create_org(services, "TONE-INACT", "Tone Inactive")
    archived_id = _create_org(services, "TONE-ARCH", "Tone Archived")
    org_service.deactivate_organization(inactive_id)
    org_service.archive_organization(archived_id)

    admin.setOrganizationStatusFilter("")
    admin.refresh()

    active_label = _row_by_id(admin, active_id)["statusLabel"]
    inactive_label = _row_by_id(admin, inactive_id)["statusLabel"]
    archived_label = _row_by_id(admin, archived_id)["statusLabel"]

    # DataTable/StatusChip only render an explicit tone for a {"label",
    # "tone"} dict -- a plain string always falls back to "neutral" (see
    # data_table_model.py). Asserting the dict shape here is what actually
    # proves the presenter (not QML) owns the status->tone mapping.
    assert active_label == {"label": "Active", "tone": "success"}
    assert inactive_label == {"label": "Inactive", "tone": "neutral"}
    assert archived_label == {"label": "Archived", "tone": "neutral"}


def test_bulk_archive_routes_through_the_canonical_bulk_service_method(services, qapp) -> None:
    _catalog, admin = _build_admin_workspace(services)
    org_a = _create_org(services, "BULK-ARCH-A", "Bulk Archive A")
    org_b = _create_org(services, "BULK-ARCH-B", "Bulk Archive B")
    admin.refresh()

    admin.setOrganizationBulkSelection(org_a, True)
    admin.setOrganizationBulkSelection(org_b, True)
    result = admin.bulkArchiveOrganizations()
    assert result["ok"] is True, result
    assert admin.selectedOrganizationIds == []

    org_service = services["organization_service"]
    all_orgs = {o.id: o for o in org_service.list_organizations(status=None)}
    assert all_orgs[org_a].status == "archived"
    assert all_orgs[org_b].status == "archived"

    # Archived is terminal -- a second archive attempt on the same
    # selection must fail clearly rather than silently no-op or partially
    # apply (see OrganizationService._require_valid_organization_transition).
    admin.setOrganizationBulkSelection(org_a, True)
    result = admin.bulkArchiveOrganizations()
    assert result["ok"] is False
    all_orgs = {o.id: o for o in org_service.list_organizations(status=None)}
    assert all_orgs[org_a].status == "archived"


def test_provision_and_update_commands_carry_no_lifecycle_field() -> None:
    """Create is always ACTIVE and Edit never touches lifecycle state --
    both are enforced structurally here (no field exists to set), not just
    by convention, so a future edit can't quietly reintroduce an
    is_enabled/status parameter on either command."""
    provision_fields = {f.name for f in dataclasses.fields(OrganizationProvisionCommand)}
    update_fields = {f.name for f in dataclasses.fields(OrganizationUpdateCommand)}
    for forbidden in ("is_enabled", "status", "enabled"):
        assert forbidden not in provision_fields
        assert forbidden not in update_fields
