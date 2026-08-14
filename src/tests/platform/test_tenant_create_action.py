"""New "Create Tenant" action -- Tenant Management previously had no create
UI at all (Refresh/Switch only), while tenant provisioning already existed
backend-only via TenantAdminService.create_tenant(). Adds the missing
desktop API method, presenter method, and controller slot, mirroring the
already-working Organizations "Create Organization" flow.
"""
from __future__ import annotations

import pytest

from src.core.platform.api.desktop.tenant.tenancy.tenant import PlatformTenantDesktopApi
from src.core.platform.api.desktop.tenant.tenancy.models.tenant import TenantCreateCommand
from src.ui_qml.platform.presenters.tenants.tenant_switcher_presenter import TenantSwitcherPresenter


def _build_tenant_api(services) -> PlatformTenantDesktopApi:
    return PlatformTenantDesktopApi(
        tenant_admin_service=services["tenant_admin_service"],
        tenant_context_service=services["tenant_context_service"],
        tenant_membership_service=services.get("tenant_membership_service"),
    )


def test_desktop_api_create_tenant(services):
    api = _build_tenant_api(services)

    result = api.create_tenant(TenantCreateCommand(tenant_code="ACME", display_name="Acme Corp"))

    assert result.ok
    assert result.data.tenant_code == "ACME"
    assert result.data.display_name == "Acme Corp"


def test_desktop_api_create_tenant_duplicate_code_fails(services):
    api = _build_tenant_api(services)
    api.create_tenant(TenantCreateCommand(tenant_code="DUPE", display_name="First"))

    result = api.create_tenant(TenantCreateCommand(tenant_code="DUPE", display_name="Second"))

    assert not result.ok
    assert result.error.code == "TENANT_CODE_CONFLICT"


def test_presenter_create_tenant_builds_command_from_payload(services):
    api = _build_tenant_api(services)
    presenter = TenantSwitcherPresenter(tenant_api=api)

    result = presenter.create_tenant({"tenantCode": "PRESENTER-T1", "displayName": "Presenter Tenant"})

    assert result.ok
    assert result.data.tenant_code == "PRESENTER-T1"


def test_presenter_create_tenant_without_api_returns_preview_error():
    presenter = TenantSwitcherPresenter(tenant_api=None)

    result = presenter.create_tenant({"tenantCode": "X", "displayName": "Y"})

    assert not result.ok


def test_new_tenant_appears_in_accessible_tenant_list(services):
    api = _build_tenant_api(services)
    api.create_tenant(TenantCreateCommand(tenant_code="LIST-T1", display_name="List Tenant"))

    presenter = TenantSwitcherPresenter(tenant_api=api)
    tenants = presenter.build_tenant_list()

    assert any(t.tenant_code == "LIST-T1" for t in tenants)
