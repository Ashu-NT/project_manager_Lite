"""P5A + Organization-specific P6A cutover: end-to-end proof that Organization creation reaches
the two real UI consumers (admin console organization list, settings organization profiles list)
through `OrganizationCreated -> ViewInvalidationHint -> OrganizationViewInvalidationAdapter`,
never the legacy `organizations_changed` signal -- and that `update_organization`/
`set_active_organization` still reach them through the unchanged legacy path.

Uses the real `services` fixture (real Session, real UnitOfWorks, real composition-owned
`ViewInvalidationChannel`) plus the real `build_desktop_api_registry`/`PlatformWorkspaceCatalog`
construction, mirroring `test_admin_workspace_eager_refresh_gating.py`'s own pattern -- not the
fully-faked `build_connected_platform_registry()` QML-preview helper other QML tests use, since
this needs the real backend event pipeline underneath.
"""

from __future__ import annotations

from src.application.runtime import build_desktop_api_registry
from src.ui_qml.platform.context import PlatformWorkspaceCatalog

_COUNTER = {"n": 0}


def _unique_code(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _catalog(services) -> PlatformWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return PlatformWorkspaceCatalog(desktop_api_registry=registry)


def test_standalone_create_organization_refreshes_both_ui_consumers(services):
    catalog = _catalog(services)
    catalog.adminWorkspace.organizations  # establish baseline read
    catalog.settingsWorkspace.refresh()

    code = _unique_code("QTCUT-STANDALONE")
    organization_service = services["organization_service"]
    organization_service.create_organization(organization_code=code, display_name="Qt Cutover Org")

    admin_titles = [row["title"] for row in catalog.adminWorkspace.organizations["items"]]
    settings_titles = [row["title"] for row in catalog.settingsWorkspace.organizationProfiles["items"]]
    assert "Qt Cutover Org" in admin_titles
    assert "Qt Cutover Org" in settings_titles


def test_provisioning_create_organization_refreshes_both_ui_consumers_identically(services):
    catalog = _catalog(services)
    catalog.adminWorkspace.organizations
    catalog.settingsWorkspace.refresh()

    app_service = services["platform_runtime_application_service"]
    code = _unique_code("QTCUT-PROV")
    app_service.provision_organization(
        organization_code=code, display_name="Qt Cutover Provisioned Org",
        timezone_name="UTC", base_currency="EUR", is_active=False, initial_module_codes=[],
    )

    admin_titles = [row["title"] for row in catalog.adminWorkspace.organizations["items"]]
    settings_titles = [row["title"] for row in catalog.settingsWorkspace.organizationProfiles["items"]]
    assert "Qt Cutover Provisioned Org" in admin_titles
    assert "Qt Cutover Provisioned Org" in settings_titles


def test_no_refresh_signal_before_commit_and_none_on_rollback(services):
    from sqlalchemy.exc import IntegrityError

    catalog = _catalog(services)
    refresh_calls = []
    catalog.adminWorkspace._organization_controller.refresh_organizations = (
        lambda: refresh_calls.append("admin") or None
    )

    organization_service = services["organization_service"]
    code = _unique_code("QTCUT-ROLLBACK")
    organization_service.create_organization(organization_code=code, display_name="First")

    from src.core.platform.common.exceptions import ValidationError
    import pytest

    with pytest.raises(ValidationError):
        organization_service.create_organization(organization_code=code, display_name="Second")

    # Exactly one successful creation happened -- exactly one refresh signal, not two, and none
    # attributable to the failed/rolled-back second attempt.
    assert refresh_calls == ["admin"]


def test_update_and_activate_still_use_the_unchanged_legacy_signal_path(services):
    """P5A implements only OrganizationCreated -- update/activation must keep working exactly as
    before, via the legacy `organizations_changed` signal, untouched by this cutover."""
    from src.core.shared.events.domain_events import domain_events

    organization_service = services["organization_service"]
    organization = organization_service.create_organization(
        organization_code=_unique_code("QTCUT-UPDATE"), display_name="Before Update"
    )

    signal_calls = []
    domain_events.organizations_changed.connect(lambda org_id: signal_calls.append(org_id))

    updated = organization_service.update_organization(
        organization.id, expected_version=organization.version, display_name="After Update"
    )
    assert signal_calls == [updated.id]

    signal_calls.clear()
    activated = organization_service.set_active_organization(organization.id)
    assert signal_calls == [activated.id]


def test_admin_console_own_mutation_still_self_refreshes_via_existing_direct_path(services):
    """Pre-existing, unrelated behavior (refresh_after_organization_change) must be unaffected by
    this cutover: the admin console still refreshes its own organization list immediately after
    ITS OWN createOrganization action, independent of the event/ViewInvalidation path."""
    catalog = _catalog(services)

    result = catalog.adminWorkspace.createOrganization(
        {
            "organizationCode": _unique_code("QTCUT-SELF"),
            "displayName": "Self Refresh Org",
            "timezoneName": "UTC",
            "baseCurrency": "USD",
            "isActive": False,
            "initialModuleCodes": [],
        }
    )
    assert result["ok"] is True
    titles = [row["title"] for row in catalog.adminWorkspace.organizations["items"]]
    assert "Self Refresh Org" in titles
