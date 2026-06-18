"""Tests for PlatformTenantDesktopApi."""
from __future__ import annotations

import pytest

from src.api.desktop.platform.tenant import PlatformTenantDesktopApi
from src.api.desktop.platform.models.tenant import TenantDto
from src.core.platform.infrastructure.persistence.repositories.org import (
    SqlAlchemyOrganizationRepository,
)
from src.core.platform.infrastructure.persistence.repositories.tenant import (
    SqlAlchemyTenantRepository,
)
from src.core.platform.infrastructure.persistence.repositories.user_tenant import (
    SqlAlchemyUserTenantMembershipRepository,
)
from src.core.platform.org.domain import Organization
from src.core.platform.tenancy.application.tenant_admin_service import TenantAdminService
from src.core.platform.tenancy.domain.user_tenant_membership import UserTenantMembership
from src.core.platform.tenancy.tenant_context import TenantContextService


def _build_api(services) -> PlatformTenantDesktopApi:
    return PlatformTenantDesktopApi(
        tenant_admin_service=services["tenant_admin_service"],
        tenant_context_service=services["tenant_context_service"],
    )


# ---------------------------------------------------------------------------
# list_accessible_tenants
# ---------------------------------------------------------------------------

def test_list_accessible_tenants_returns_dto_tuple(services):
    api = _build_api(services)
    result = api.list_accessible_tenants()
    assert result.ok
    assert isinstance(result.data, tuple)
    # admin session should see at least the default tenant
    assert len(result.data) >= 1
    for item in result.data:
        assert isinstance(item, TenantDto)
        assert item.id
        assert item.tenant_code
        assert item.tenant_status in {"active", "suspended", "archived"}


def test_list_accessible_tenants_includes_newly_created(services):
    api = _build_api(services)
    admin_svc = services["tenant_admin_service"]
    new_tenant = admin_svc.create_tenant("P2DAPI-NEW", "API New Tenant")
    services["session"].flush()

    result = api.list_accessible_tenants()
    assert result.ok
    ids = {t.id for t in result.data}
    assert new_tenant.id in ids


# ---------------------------------------------------------------------------
# get_active_tenant
# ---------------------------------------------------------------------------

def test_get_active_tenant_returns_dto(services):
    api = _build_api(services)
    result = api.get_active_tenant()
    assert result.ok
    # Default tenant is active at startup
    if result.data is not None:
        assert isinstance(result.data, TenantDto)
        assert result.data.is_active


# ---------------------------------------------------------------------------
# switch_to_tenant
# ---------------------------------------------------------------------------

def test_switch_to_tenant_returns_new_tenant_dto(services):
    api = _build_api(services)
    admin_svc = services["tenant_admin_service"]
    new_tenant = admin_svc.create_tenant("P2DAPI-SW", "API Switch Tenant")
    services["session"].flush()

    result = api.switch_to_tenant(new_tenant.id)
    assert result.ok
    assert result.data is not None
    assert isinstance(result.data, TenantDto)
    assert result.data.id == new_tenant.id
    assert result.data.tenant_code == "P2DAPI-SW"


def test_switch_to_tenant_updates_active_tenant(services):
    api = _build_api(services)
    admin_svc = services["tenant_admin_service"]
    new_tenant = admin_svc.create_tenant("P2DAPI-ACTIVE", "API Active Tenant")
    services["session"].flush()

    api.switch_to_tenant(new_tenant.id)

    active = api.get_active_tenant()
    assert active.ok
    assert active.data is not None
    assert active.data.id == new_tenant.id


def test_switch_to_suspended_tenant_fails(services):
    api = _build_api(services)
    admin_svc = services["tenant_admin_service"]
    t = admin_svc.create_tenant("P2DAPI-SUSP", "API Susp Tenant")
    services["session"].flush()
    admin_svc.suspend_tenant(t.id)
    services["session"].flush()

    result = api.switch_to_tenant(t.id)
    assert not result.ok
    assert result.error is not None
    assert result.error.code == "TENANT_SUSPENDED"


def test_switch_to_archived_tenant_fails(services):
    api = _build_api(services)
    admin_svc = services["tenant_admin_service"]
    t = admin_svc.create_tenant("P2DAPI-ARCH", "API Arch Tenant")
    services["session"].flush()
    admin_svc.archive_tenant(t.id)
    services["session"].flush()

    result = api.switch_to_tenant(t.id)
    assert not result.ok
    assert result.error is not None
    assert result.error.code == "TENANT_ARCHIVED"


def test_switch_to_nonexistent_tenant_fails(services):
    api = _build_api(services)
    result = api.switch_to_tenant("00000000-0000-0000-0000-000000000000")
    assert not result.ok
    assert result.error is not None
    assert result.error.code == "TENANT_NOT_FOUND"
