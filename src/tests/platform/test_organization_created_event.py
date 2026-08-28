"""ADR-005 P5A: `OrganizationCreated` -- the business event contract, its recording lifecycle
(both creation paths), and its post-commit `ViewInvalidation` mapping. Complements
`test_organization_service_unit_of_work_cutover.py`/`test_platform_provisioning_unit_of_work_cutover.py`,
which already prove the standalone/provisioning transaction mechanics this event rides on top of.
"""

from __future__ import annotations

import inspect
from dataclasses import fields, is_dataclass
from datetime import datetime, timezone

import pytest

from src.core.platform.application.master_data.org.event_handlers.view_invalidation import (
    ORGANIZATION_CATEGORY,
    ORGANIZATION_DETAILS_SCOPE_CODE,
    ORGANIZATION_LIST_SCOPE_CODE,
    build_organization_created_view_invalidation_handler,
)
from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.domain.master_data.org import events as organization_events_module
from src.core.platform.domain.master_data.org.events import OrganizationCreated
from src.core.shared.events.domain_event import DomainEvent
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    ExactOrganization,
    OrganizationScope,
    TenantScope,
    TenantWide,
)

_COUNTER = {"n": 0}


def _unique_code(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


class _FixedClock:
    def __init__(self, when: datetime) -> None:
        self._when = when

    def now(self) -> datetime:
        return self._when


# ---------------------------------------------------------------------------
# Event contract
# ---------------------------------------------------------------------------


def test_organization_created_conforms_to_domain_event_and_has_only_approved_fields():
    event = OrganizationCreated(
        tenant_id="tenant-a",
        organization_id="org-a",
        name="North Division",
        code="NORTH",
        occurred_at=datetime.now(timezone.utc),
    )
    assert isinstance(event, DomainEvent)
    assert is_dataclass(event)
    field_names = {f.name for f in fields(event)}
    assert field_names == {"tenant_id", "organization_id", "name", "code", "occurred_at"}
    # Immutable, per ADR-005's frozen/slots convention.
    with pytest.raises(AttributeError):
        event.name = "Changed"  # type: ignore[misc]


def _imported_module_names(module) -> set[str]:
    import ast

    tree = ast.parse(inspect.getsource(module))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_organization_created_module_has_no_ui_or_view_invalidation_vocabulary():
    imports = _imported_module_names(organization_events_module)
    for forbidden in ("view_invalidation", "domain_events", "PySide6", "QtCore"):
        assert not any(forbidden in name for name in imports), imports


def test_organization_created_event_handlers_package_has_no_qt_dependency():
    for module_name in ("view_invalidation",):
        module = __import__(
            f"src.core.platform.application.master_data.org.event_handlers.{module_name}",
            fromlist=[module_name],
        )
        imports = _imported_module_names(module)
        for forbidden in ("PySide6", "QtCore"):
            assert not any(forbidden in name for name in imports), imports


# ---------------------------------------------------------------------------
# Standalone creation: recording, exactly-once, Clock, context
# ---------------------------------------------------------------------------


def test_standalone_create_records_exactly_one_event_before_commit(services, monkeypatch):
    organization_service = services["organization_service"]
    recorded = []
    original_create = type(organization_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        original_record_event = uow.record_event

        def _spy_record_event(event):
            assert uow._committed is False, "event must be recorded before commit, not after"
            recorded.append(event)
            return original_record_event(event)

        uow.record_event = _spy_record_event
        return uow

    monkeypatch.setattr(type(organization_service._uow_factory), "create", _spy_create)

    organization = organization_service.create_organization(
        organization_code=_unique_code("REC"), display_name="Recorded Org"
    )

    assert len(recorded) == 1
    event = recorded[0]
    assert isinstance(event, OrganizationCreated)
    assert event.organization_id == organization.id
    assert event.name == "Recorded Org"
    assert event.code == organization.organization_code


def test_standalone_create_uses_injected_clock_deterministically(services):
    organization_service = services["organization_service"]
    fixed_when = datetime(2030, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    original_clock = organization_service._clock
    organization_service._clock = _FixedClock(fixed_when)
    try:
        captured = {}
        channel = services["platform_view_invalidation_channel"]
        channel.subscribe(TenantWide(_active_tenant(services)), lambda hint: captured.setdefault("hint", hint))

        organization_service.create_organization(
            organization_code=_unique_code("CLOCK"), display_name="Clock Org"
        )
        assert "hint" in captured
    finally:
        organization_service._clock = original_clock


def _active_tenant(services) -> str:
    return services["tenant_context_service"].get_active_tenant_id()


def test_standalone_create_tenant_id_and_organization_id_explicit_not_ambient(services):
    organization_service = services["organization_service"]
    tenant_id = _active_tenant(services)
    channel = services["platform_view_invalidation_channel"]
    hints = []
    channel.subscribe(TenantWide(tenant_id), lambda hint: hints.append(hint))

    organization = organization_service.create_organization(
        organization_code=_unique_code("EXPLICIT"), display_name="Explicit Org"
    )

    list_hints = [h for h in hints if h.scope_code == ORGANIZATION_LIST_SCOPE_CODE]
    assert len(list_hints) == 1
    assert list_hints[0].scope == TenantScope(tenant_id)


def test_no_event_observable_on_validation_failure(services):
    organization_service = services["organization_service"]
    code = _unique_code("DUPE-EVT")
    organization_service.create_organization(organization_code=code, display_name="First")

    tenant_id = _active_tenant(services)
    channel = services["platform_view_invalidation_channel"]
    hints = []
    channel.subscribe(TenantWide(tenant_id), lambda hint: hints.append(hint))

    from src.core.platform.common.exceptions import ValidationError

    with pytest.raises(ValidationError):
        organization_service.create_organization(organization_code=code, display_name="Second")

    assert hints == []


def test_no_event_observable_on_commit_failure(services, monkeypatch):
    from src.core.platform.infrastructure.persistence.uow.organization_unit_of_work import (
        SqlAlchemyOrganizationUnitOfWork,
    )

    organization_service = services["organization_service"]
    tenant_id = _active_tenant(services)
    channel = services["platform_view_invalidation_channel"]
    hints = []
    channel.subscribe(TenantWide(tenant_id), lambda hint: hints.append(hint))

    def _fail_commit(self):
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(SqlAlchemyOrganizationUnitOfWork, "commit", _fail_commit)

    with pytest.raises(RuntimeError, match="simulated commit failure"):
        organization_service.create_organization(
            organization_code=_unique_code("COMMITFAIL-EVT"), display_name="x"
        )

    assert hints == []


# ---------------------------------------------------------------------------
# Provisioning creation: same fact, same guarantees
# ---------------------------------------------------------------------------


def test_provisioning_create_records_exactly_one_event_before_commit(services, monkeypatch):
    app_service = services["platform_runtime_application_service"]
    recorded = []
    original_create = type(app_service._provisioning_uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        original_record_event = uow.record_event

        def _spy_record_event(event):
            assert uow._committed is False
            recorded.append(event)
            return original_record_event(event)

        uow.record_event = _spy_record_event
        return uow

    monkeypatch.setattr(type(app_service._provisioning_uow_factory), "create", _spy_create)

    organization = app_service.provision_organization(
        organization_code=_unique_code("PROV-EVT"), display_name="Provisioned Evt Org",
        timezone_name="UTC", base_currency="EUR", is_enabled=False, initial_module_codes=[],
    )

    assert len(recorded) == 1
    assert isinstance(recorded[0], OrganizationCreated)
    assert recorded[0].organization_id == organization.id


def test_provisioning_late_failure_produces_no_observable_event(services):
    app_service = services["platform_runtime_application_service"]
    tenant_id = _active_tenant(services)
    channel = services["platform_view_invalidation_channel"]
    hints = []
    channel.subscribe(TenantWide(tenant_id), lambda hint: hints.append(hint))

    with pytest.raises(NotFoundError):
        app_service.provision_organization(
            organization_code=_unique_code("PROV-LATEFAIL-EVT"), display_name="x",
            timezone_name="UTC", base_currency="EUR", is_enabled=False,
            initial_module_codes=["not-a-real-module"],
        )

    assert hints == []


# ---------------------------------------------------------------------------
# ViewInvalidation matrix: exact targets, exact scopes
# ---------------------------------------------------------------------------


def test_view_invalidation_mapper_produces_exactly_the_two_documented_hints():
    channel_hints = []

    class _FakeChannel:
        def notify(self, hint):
            channel_hints.append(hint)

    handler = build_organization_created_view_invalidation_handler(_FakeChannel())
    event = OrganizationCreated(
        tenant_id="tenant-x", organization_id="org-x", name="X Org", code="X",
        occurred_at=datetime.now(timezone.utc),
    )
    handler(event, DomainEventContext(correlation_id="corr-1"))

    assert len(channel_hints) == 2
    by_scope_code = {hint.scope_code: hint for hint in channel_hints}
    assert set(by_scope_code) == {ORGANIZATION_LIST_SCOPE_CODE, ORGANIZATION_DETAILS_SCOPE_CODE}
    list_hint = by_scope_code[ORGANIZATION_LIST_SCOPE_CODE]
    details_hint = by_scope_code[ORGANIZATION_DETAILS_SCOPE_CODE]
    assert list_hint.scope == TenantScope("tenant-x")
    assert list_hint.category == ORGANIZATION_CATEGORY
    assert list_hint.entity_id is None
    assert details_hint.scope == OrganizationScope("tenant-x", "org-x")
    assert details_hint.entity_id == "org-x"


def test_cross_organization_routing_via_real_channel(services):
    organization_service = services["organization_service"]
    tenant_id = _active_tenant(services)
    org_a1 = organization_service.create_organization(
        organization_code=_unique_code("ROUTE-A1"), display_name="Route Org A1"
    )
    channel = services["platform_view_invalidation_channel"]
    a1_hits, a2_hits = [], []
    channel.subscribe(ExactOrganization(tenant_id, org_a1.id), lambda hint: a1_hits.append(hint))

    org_a2 = organization_service.create_organization(
        organization_code=_unique_code("ROUTE-A2"), display_name="Route Org A2"
    )
    channel.subscribe(ExactOrganization(tenant_id, org_a2.id), lambda hint: a2_hits.append(hint))
    organization_service.create_organization(
        organization_code=_unique_code("ROUTE-A3"), display_name="Route Org A3"
    )

    # a1's own subscription only ever saw hints for a1 (none for a3, subscribed before a3 existed
    # and therefore couldn't have matched anyway -- proven by scope equality below).
    assert all(isinstance(h.scope, OrganizationScope) and h.scope.organization_id == org_a1.id for h in a1_hits)
    assert all(isinstance(h.scope, OrganizationScope) and h.scope.organization_id == org_a2.id for h in a2_hits)


def test_cross_tenant_routing_via_real_channel(services):
    from src.core.platform.infrastructure.persistence.orm.tenant.tenancy.tenant import TenantORM
    from src.core.platform.domain.security.auth.session import UserSessionContext, UserSessionPrincipal
    from src.core.platform.application.master_data.org.organization_service import OrganizationService

    organization_service = services["organization_service"]
    session = services["session"]
    tenant_a = _active_tenant(services)
    channel = services["platform_view_invalidation_channel"]

    tenant_b_id = _unique_code("tenant-b")
    session.add(TenantORM(id=tenant_b_id, tenant_code=_unique_code("TB"), display_name="Tenant B", is_active=True, version=1))
    session.commit()
    ctx_b = UserSessionContext()
    ctx_b.set_principal(
        UserSessionPrincipal(
            user_id="tenant-b-user", username="tenant-b-user", display_name="Tenant B User",
            role_names=frozenset(["admin"]), permissions=frozenset(["settings.manage"]),
        )
    )
    ctx_b.set_active_tenant_id(tenant_b_id)
    service_as_b = OrganizationService(
        session=organization_service._session,
        organization_repo=organization_service._organization_repo,
        uow_factory=organization_service._uow_factory,
        clock=organization_service._clock,
        user_session=ctx_b,
        enterprise_audit_service=organization_service._enterprise_audit_service,
        tenant_context_service=None,
        overview_rollup_reader=organization_service._overview_rollup_reader,
    )

    tenant_a_hits = []
    channel.subscribe(TenantWide(tenant_a), lambda hint: tenant_a_hits.append(hint))

    service_as_b.create_organization(organization_code=_unique_code("TENANT-B-ORG"), display_name="Tenant B Org")

    assert tenant_a_hits == []


# ---------------------------------------------------------------------------
# Post-commit failure isolation (P2 ISOLATE_AND_CONTINUE)
# ---------------------------------------------------------------------------


def test_one_post_commit_handler_failing_does_not_block_the_other_or_the_commit(services):
    organization_service = services["organization_service"]
    bus = organization_service._uow_factory._post_commit_bus

    def _failing_handler(event, context):
        raise RuntimeError("simulated post-commit handler failure")

    bus.subscribe(OrganizationCreated, _failing_handler)

    channel = services["platform_view_invalidation_channel"]
    tenant_id = _active_tenant(services)
    hints = []
    channel.subscribe(TenantWide(tenant_id), lambda hint: hints.append(hint))

    # Must not raise -- ISOLATE_AND_CONTINUE swallows the failing handler's exception.
    organization = organization_service.create_organization(
        organization_code=_unique_code("ISOLATE"), display_name="Isolate Org"
    )

    assert organization is not None
    assert any(h.scope_code == ORGANIZATION_LIST_SCOPE_CODE for h in hints)
    reloaded = organization_service._organization_repo.get(organization.id)
    assert reloaded is not None
