"""Tests for Phase 2C: PlatformEvent persistence and TenantAdminService emission.

Covers:
  1. create_tenant emits a platform_event with severity=low and correct metadata
  2. suspend_tenant emits a platform_event with severity=medium
  3. archive_tenant emits a platform_event with severity=high and captures old_status
  4. restore_tenant emits a platform_event with severity=medium
  5. PlatformEventRepository.update() raises OperationNotPermittedError
  6. PlatformEventRepository.delete() raises OperationNotPermittedError
  7. list_for_tenant returns only events scoped to the given tenant
  8. list_for_resource filters by resource_type and resource_id
"""
from __future__ import annotations

import pytest

from src.core.platform.common.exceptions import OperationNotPermittedError
from src.core.platform.infrastructure.persistence.repositories.events.platform_events.platform_events import (
    SqlAlchemyPlatformEventRepository,
)
from src.core.platform.infrastructure.persistence.repositories.tenant import SqlAlchemyTenantRepository
from src.core.platform.infrastructure.persistence.repositories.user_tenant import (
    SqlAlchemyUserTenantMembershipRepository,
)
from src.core.platform.domain.events.platform_events.platform_event import PlatformEvent
from src.core.platform.tenancy.application.tenant_admin_service import TenantAdminService
from src.core.platform.tenancy.domain.tenant import (
    TENANT_STATUS_ACTIVE,
    TENANT_STATUS_ARCHIVED,
    TENANT_STATUS_SUSPENDED,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_svc_with_events(services) -> tuple[TenantAdminService, SqlAlchemyPlatformEventRepository]:
    session = services["session"]
    event_repo = SqlAlchemyPlatformEventRepository(session)
    svc = TenantAdminService(
        session=session,
        tenant_repo=SqlAlchemyTenantRepository(session),
        user_tenant_repo=SqlAlchemyUserTenantMembershipRepository(session),
        user_session=services["user_session"],
        platform_event_repo=event_repo,
    )
    return svc, event_repo


# ---------------------------------------------------------------------------
# 1–4. Emission tests
# ---------------------------------------------------------------------------

def test_create_tenant_emits_event_low_severity(services):
    svc, event_repo = _make_svc_with_events(services)
    tenant = svc.create_tenant("P2C-CREATE1", "Create Emission Test")
    services["session"].flush()

    events = event_repo.list_for_tenant(tenant.id)
    assert len(events) == 1
    evt = events[0]
    assert evt.operation == "create_tenant"
    assert evt.severity == "low"
    assert evt.resource_type == "tenant"
    assert evt.resource_id == tenant.id
    assert evt.metadata["tenant_code"] == "P2C-CREATE1"
    assert evt.metadata["display_name"] == "Create Emission Test"


def test_suspend_tenant_emits_event_medium_severity(services):
    svc, event_repo = _make_svc_with_events(services)
    tenant = svc.create_tenant("P2C-SUSP1", "Suspend Emission Test")
    services["session"].flush()

    # Clear create event for cleaner assertion
    svc.suspend_tenant(tenant.id)
    services["session"].flush()

    events = event_repo.list_for_tenant(tenant.id)
    suspend_events = [e for e in events if e.operation == "suspend_tenant"]
    assert len(suspend_events) == 1
    evt = suspend_events[0]
    assert evt.severity == "medium"
    assert evt.metadata["old_status"] == TENANT_STATUS_ACTIVE
    assert evt.metadata["new_status"] == TENANT_STATUS_SUSPENDED
    assert evt.metadata["tenant_code"] == "P2C-SUSP1"


def test_archive_tenant_emits_event_high_severity_with_old_status(services):
    svc, event_repo = _make_svc_with_events(services)
    tenant = svc.create_tenant("P2C-ARCH1", "Archive Emission Test")
    services["session"].flush()
    svc.suspend_tenant(tenant.id)
    services["session"].flush()

    svc.archive_tenant(tenant.id)
    services["session"].flush()

    events = event_repo.list_for_tenant(tenant.id)
    archive_events = [e for e in events if e.operation == "archive_tenant"]
    assert len(archive_events) == 1
    evt = archive_events[0]
    assert evt.severity == "high"
    assert evt.metadata["old_status"] == TENANT_STATUS_SUSPENDED
    assert evt.metadata["new_status"] == TENANT_STATUS_ARCHIVED


def test_restore_tenant_emits_event_medium_severity(services):
    svc, event_repo = _make_svc_with_events(services)
    tenant = svc.create_tenant("P2C-REST1", "Restore Emission Test")
    services["session"].flush()
    svc.archive_tenant(tenant.id)
    services["session"].flush()

    svc.restore_tenant(tenant.id)
    services["session"].flush()

    events = event_repo.list_for_tenant(tenant.id)
    restore_events = [e for e in events if e.operation == "restore_tenant"]
    assert len(restore_events) == 1
    evt = restore_events[0]
    assert evt.severity == "medium"
    assert evt.metadata["old_status"] == TENANT_STATUS_ARCHIVED
    assert evt.metadata["new_status"] == TENANT_STATUS_ACTIVE


# ---------------------------------------------------------------------------
# 5–6. Append-only enforcement
# ---------------------------------------------------------------------------

def test_platform_event_repo_update_raises(services):
    event_repo = SqlAlchemyPlatformEventRepository(services["session"])
    dummy = PlatformEvent.create(
        operation="test.op",
        actor_user_id=None,
        tenant_id="does-not-matter",
        resource_type="tenant",
        resource_id="does-not-matter",
    )
    with pytest.raises(OperationNotPermittedError) as exc:
        event_repo.update(dummy)
    assert exc.value.code == "PLATFORM_EVENT_IMMUTABLE"


def test_platform_event_repo_delete_raises(services):
    event_repo = SqlAlchemyPlatformEventRepository(services["session"])
    with pytest.raises(OperationNotPermittedError) as exc:
        event_repo.delete("any-id")
    assert exc.value.code == "PLATFORM_EVENT_IMMUTABLE"


# ---------------------------------------------------------------------------
# 7–8. Scoping
# ---------------------------------------------------------------------------

def test_list_for_tenant_scoped_to_tenant(services):
    svc_a, event_repo = _make_svc_with_events(services)
    tenant_a = svc_a.create_tenant("P2C-SCOPE-A", "Scope Tenant A")
    services["session"].flush()

    svc_b, _ = _make_svc_with_events(services)
    tenant_b = svc_b.create_tenant("P2C-SCOPE-B", "Scope Tenant B")
    services["session"].flush()

    events_a = event_repo.list_for_tenant(tenant_a.id)
    events_b = event_repo.list_for_tenant(tenant_b.id)

    tenant_ids_a = {e.tenant_id for e in events_a}
    tenant_ids_b = {e.tenant_id for e in events_b}

    assert tenant_ids_a == {tenant_a.id}
    assert tenant_ids_b == {tenant_b.id}
    assert tenant_a.id not in tenant_ids_b
    assert tenant_b.id not in tenant_ids_a


def test_list_for_resource_filters_correctly(services):
    svc, event_repo = _make_svc_with_events(services)
    tenant_x = svc.create_tenant("P2C-RES-X", "Resource Filter X")
    tenant_y = svc.create_tenant("P2C-RES-Y", "Resource Filter Y")
    services["session"].flush()

    events_x = event_repo.list_for_resource(tenant_x.id, "tenant", tenant_x.id)
    events_y = event_repo.list_for_resource(tenant_y.id, "tenant", tenant_y.id)

    assert all(e.resource_id == tenant_x.id for e in events_x)
    assert all(e.resource_id == tenant_y.id for e in events_y)
    assert len(events_x) >= 1
    assert len(events_y) >= 1
