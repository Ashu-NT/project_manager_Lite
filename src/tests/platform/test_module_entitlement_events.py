"""ADR-005 P5B-2: `ModuleLicensed`/`ModuleLicenseRevoked`/`ModuleEnabled`/`ModuleDisabled`/
`ModuleLifecycleTransitioned` -- the five Module Entitlement business events, their recording
lifecycle at each P5B-SEM/P5B-1 semantic command boundary, and the no-event/single-event
guarantees P5B-SEM's design decided. Complements
`test_module_entitlement_transaction_convergence.py` (transaction/scope mechanics) and
`test_module_entitlement_semantic_commands.py` (the state machine itself).

P5B-3 (see `test_module_entitlement_view_invalidation_qt_cutover.py`) later mapped these events
onto `ViewInvalidationHint`, migrated the real Qt consumers, and retired the legacy
`modules_changed` signal this file no longer tests directly.
"""

from __future__ import annotations

import inspect
from dataclasses import fields, is_dataclass
from datetime import datetime, timezone

import pytest

from src.core.platform.domain.tenant.modules import events as module_events_module
from src.core.platform.domain.tenant.modules.events import (
    ModuleDisabled,
    ModuleEnabled,
    ModuleLicenseRevoked,
    ModuleLicensed,
    ModuleLifecycleTransitioned,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.infrastructure.persistence.uow.module_entitlement_unit_of_work import (
    SqlAlchemyModuleEntitlementUnitOfWork,
)
from src.core.shared.events.domain_event import DomainEvent

_COUNTER = {"n": 0}


def _unique_code(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


class _FixedClock:
    def __init__(self, when: datetime) -> None:
        self._when = when

    def now(self) -> datetime:
        return self._when


def _spy_recorded_events(catalog, monkeypatch) -> list:
    recorded = []
    original_create = type(catalog._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        original_record_event = uow.record_event

        def _spy_record_event(event):
            assert uow._committed is False, "event must be recorded before commit, not after"
            recorded.append(event)
            return original_record_event(event)

        uow.record_event = _spy_record_event
        return uow

    monkeypatch.setattr(type(catalog._uow_factory), "create", _spy_create)
    return recorded


def _active_tenant(services) -> str:
    return services["tenant_context_service"].get_active_tenant_id()


# ---------------------------------------------------------------------------
# Event contract / architecture guards
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "event_cls,expected_fields",
    [
        (ModuleLicensed, {"tenant_id", "organization_id", "module_code", "occurred_at"}),
        (ModuleLicenseRevoked, {"tenant_id", "organization_id", "module_code", "occurred_at"}),
        (ModuleEnabled, {"tenant_id", "organization_id", "module_code", "occurred_at"}),
        (ModuleDisabled, {"tenant_id", "organization_id", "module_code", "occurred_at"}),
        (
            ModuleLifecycleTransitioned,
            {
                "tenant_id",
                "organization_id",
                "module_code",
                "previous_lifecycle_status",
                "lifecycle_status",
                "occurred_at",
            },
        ),
    ],
)
def test_module_event_conforms_to_domain_event_and_has_only_approved_fields(event_cls, expected_fields):
    kwargs = {name: "x" for name in expected_fields if name != "occurred_at"}
    kwargs["occurred_at"] = datetime.now(timezone.utc)
    event = event_cls(**kwargs)
    assert isinstance(event, DomainEvent)
    assert is_dataclass(event)
    assert {f.name for f in fields(event)} == expected_fields
    with pytest.raises(AttributeError):
        event.module_code = "changed"  # type: ignore[misc]


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


def test_module_events_module_has_no_ui_or_view_invalidation_or_infrastructure_vocabulary():
    imports = _imported_module_names(module_events_module)
    for forbidden in ("view_invalidation", "domain_events", "PySide6", "QtCore", "ui_qml", "infrastructure"):
        assert not any(forbidden in name for name in imports), imports


def test_shared_events_package_does_not_import_module_entitlement_events():
    import src.core.shared.events.domain_event as shared_domain_event_module

    source = inspect.getsource(shared_domain_event_module)
    for forbidden in ("ModuleLicensed", "ModuleLicenseRevoked", "ModuleEnabled", "ModuleDisabled", "ModuleLifecycleTransitioned"):
        assert forbidden not in source


# ---------------------------------------------------------------------------
# License idempotency (P5B-2 step 2): confirm the P5B-1 decision before trusting it for events
# ---------------------------------------------------------------------------


def test_license_module_idempotency_preserves_trial_not_a_lifecycle_reset(services):
    catalog = services["module_catalog_service"]
    org = services["tenant_context_service"].get_active_organization()
    catalog.transition_module_lifecycle(org.id, "project_management", "trial")

    entitlement = catalog.license_module(org.id, "project_management")

    assert entitlement.licensed is True
    assert entitlement.lifecycle_status == "trial"  # not reset to "active" -- true no-op


# ---------------------------------------------------------------------------
# ModuleLicensed
# ---------------------------------------------------------------------------


def test_license_module_records_exactly_one_module_licensed(services, monkeypatch):
    catalog = services["module_catalog_service"]
    org = services["tenant_context_service"].get_active_organization()
    catalog.revoke_module_license(org.id, "project_management")
    recorded = _spy_recorded_events(catalog, monkeypatch)

    entitlement = catalog.license_module(org.id, "project_management")

    assert len(recorded) == 1
    event = recorded[0]
    assert isinstance(event, ModuleLicensed)
    assert event.tenant_id == _active_tenant(services)
    assert event.organization_id == org.id
    assert event.module_code == "project_management"
    assert entitlement.licensed is True
    assert entitlement.lifecycle_status == "active"
    assert entitlement.enabled is False


def test_license_module_on_already_licensed_module_records_zero_events(services, monkeypatch):
    catalog = services["module_catalog_service"]
    org = services["tenant_context_service"].get_active_organization()
    recorded = _spy_recorded_events(catalog, monkeypatch)

    catalog.license_module(org.id, "project_management")  # already licensed by default

    assert recorded == []


def test_license_module_uses_the_injected_clock_deterministically(services, monkeypatch):
    catalog = services["module_catalog_service"]
    org = services["tenant_context_service"].get_active_organization()
    catalog.revoke_module_license(org.id, "project_management")
    fixed_when = datetime(2030, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    original_clock = catalog._clock
    catalog._clock = _FixedClock(fixed_when)
    try:
        recorded = _spy_recorded_events(catalog, monkeypatch)
        catalog.license_module(org.id, "project_management")
        assert recorded[0].occurred_at == fixed_when
    finally:
        catalog._clock = original_clock


# ---------------------------------------------------------------------------
# ModuleLicenseRevoked
# ---------------------------------------------------------------------------


def test_revoke_module_license_records_exactly_one_module_license_revoked_and_no_others(services, monkeypatch):
    catalog = services["module_catalog_service"]
    org = services["tenant_context_service"].get_active_organization()
    recorded = _spy_recorded_events(catalog, monkeypatch)

    entitlement = catalog.revoke_module_license(org.id, "project_management")

    assert len(recorded) == 1
    event = recorded[0]
    assert isinstance(event, ModuleLicenseRevoked)
    assert event.organization_id == org.id
    assert event.module_code == "project_management"
    assert entitlement.licensed is False
    assert entitlement.enabled is False
    assert entitlement.lifecycle_status == "inactive"
    # The forced enabled=False/inactive consequence is NOT a second/third event.
    assert not any(isinstance(e, (ModuleDisabled, ModuleLifecycleTransitioned)) for e in recorded)


def test_revoke_module_license_on_already_unlicensed_module_records_zero_events(services, monkeypatch):
    catalog = services["module_catalog_service"]
    org = services["tenant_context_service"].get_active_organization()
    catalog.revoke_module_license(org.id, "project_management")
    recorded = _spy_recorded_events(catalog, monkeypatch)

    catalog.revoke_module_license(org.id, "project_management")

    assert recorded == []


# ---------------------------------------------------------------------------
# ModuleEnabled
# ---------------------------------------------------------------------------


def test_enable_module_records_exactly_one_module_enabled_from_active_and_from_trial(services, monkeypatch):
    catalog = services["module_catalog_service"]
    org = services["tenant_context_service"].get_active_organization()
    catalog.disable_module(org.id, "project_management")
    recorded = _spy_recorded_events(catalog, monkeypatch)

    catalog.enable_module(org.id, "project_management")

    assert len(recorded) == 1
    assert isinstance(recorded[0], ModuleEnabled)
    assert recorded[0].organization_id == org.id

    catalog.disable_module(org.id, "project_management")
    catalog.transition_module_lifecycle(org.id, "project_management", "trial")
    recorded.clear()
    catalog.enable_module(org.id, "project_management")

    assert len(recorded) == 1
    assert isinstance(recorded[0], ModuleEnabled)


def test_enable_module_invalid_attempts_record_zero_events(services, monkeypatch):
    catalog = services["module_catalog_service"]
    org = services["tenant_context_service"].get_active_organization()
    recorded = _spy_recorded_events(catalog, monkeypatch)

    catalog.revoke_module_license(org.id, "project_management")
    recorded.clear()
    with pytest.raises(ValidationError):
        catalog.enable_module(org.id, "project_management")
    assert recorded == []

    catalog.license_module(org.id, "project_management")
    catalog.transition_module_lifecycle(org.id, "project_management", "suspended")
    recorded.clear()
    with pytest.raises(ValidationError):
        catalog.enable_module(org.id, "project_management")
    assert recorded == []

    catalog.transition_module_lifecycle(org.id, "project_management", "expired")
    recorded.clear()
    with pytest.raises(ValidationError):
        catalog.enable_module(org.id, "project_management")
    assert recorded == []


def test_enable_module_on_already_enabled_module_records_zero_events(services, monkeypatch):
    catalog = services["module_catalog_service"]
    org = services["tenant_context_service"].get_active_organization()
    recorded = _spy_recorded_events(catalog, monkeypatch)

    catalog.enable_module(org.id, "project_management")  # already enabled by default

    assert recorded == []


# ---------------------------------------------------------------------------
# ModuleDisabled
# ---------------------------------------------------------------------------


def test_disable_module_records_exactly_one_module_disabled_license_and_lifecycle_unchanged(services, monkeypatch):
    catalog = services["module_catalog_service"]
    org = services["tenant_context_service"].get_active_organization()
    catalog.transition_module_lifecycle(org.id, "project_management", "trial")
    recorded = _spy_recorded_events(catalog, monkeypatch)

    entitlement = catalog.disable_module(org.id, "project_management")

    assert len(recorded) == 1
    assert isinstance(recorded[0], ModuleDisabled)
    assert entitlement.licensed is True
    assert entitlement.lifecycle_status == "trial"


def test_disable_module_on_already_disabled_module_records_zero_events(services, monkeypatch):
    catalog = services["module_catalog_service"]
    org = services["tenant_context_service"].get_active_organization()
    catalog.disable_module(org.id, "project_management")
    recorded = _spy_recorded_events(catalog, monkeypatch)

    catalog.disable_module(org.id, "project_management")

    assert recorded == []


# ---------------------------------------------------------------------------
# ModuleLifecycleTransitioned
# ---------------------------------------------------------------------------


def test_transition_module_lifecycle_records_previous_and_new_status(services, monkeypatch):
    catalog = services["module_catalog_service"]
    org = services["tenant_context_service"].get_active_organization()
    recorded = _spy_recorded_events(catalog, monkeypatch)

    trial = catalog.transition_module_lifecycle(org.id, "project_management", "trial")
    assert len(recorded) == 1
    assert isinstance(recorded[0], ModuleLifecycleTransitioned)
    assert recorded[0].previous_lifecycle_status == "active"
    assert recorded[0].lifecycle_status == "trial"
    assert trial.enabled is True

    recorded.clear()
    active = catalog.transition_module_lifecycle(org.id, "project_management", "active")
    assert recorded[0].previous_lifecycle_status == "trial"
    assert recorded[0].lifecycle_status == "active"
    assert active.enabled is True

    recorded.clear()
    suspended = catalog.transition_module_lifecycle(org.id, "project_management", "suspended")
    assert len(recorded) == 1
    assert recorded[0].previous_lifecycle_status == "active"
    assert recorded[0].lifecycle_status == "suspended"
    assert suspended.enabled is False
    # The forced enabled=False consequence is NOT a second ModuleDisabled event.
    assert not any(isinstance(e, ModuleDisabled) for e in recorded)

    catalog.transition_module_lifecycle(org.id, "project_management", "active")
    catalog.enable_module(org.id, "project_management")
    recorded.clear()
    expired = catalog.transition_module_lifecycle(org.id, "project_management", "expired")
    assert len(recorded) == 1
    assert recorded[0].previous_lifecycle_status == "active"
    assert recorded[0].lifecycle_status == "expired"
    assert expired.enabled is False
    assert not any(isinstance(e, ModuleDisabled) for e in recorded)


def test_transition_module_lifecycle_same_state_records_zero_events(services, monkeypatch):
    catalog = services["module_catalog_service"]
    org = services["tenant_context_service"].get_active_organization()
    recorded = _spy_recorded_events(catalog, monkeypatch)

    catalog.transition_module_lifecycle(org.id, "project_management", "active")  # already active

    assert recorded == []


# ---------------------------------------------------------------------------
# Non-active organization / cross-tenant
# ---------------------------------------------------------------------------


def test_events_carry_the_commanded_organization_not_the_active_one(services, monkeypatch):
    organization_service = services["organization_service"]
    catalog = services["module_catalog_service"]
    org_a1 = services["tenant_context_service"].get_active_organization()
    org_a2 = organization_service.create_organization(
        organization_code=_unique_code("SEMEVT"), display_name="Semantic Event Org", is_enabled=False
    )
    assert services["tenant_context_service"].get_active_organization().id == org_a1.id
    recorded = _spy_recorded_events(catalog, monkeypatch)

    catalog.disable_module(org_a2.id, "project_management")

    assert services["tenant_context_service"].get_active_organization().id == org_a1.id  # never switched
    assert len(recorded) == 1
    assert recorded[0].organization_id == org_a2.id
    assert recorded[0].organization_id != org_a1.id


def test_command_against_a_foreign_tenant_organization_is_rejected_with_no_event(services, monkeypatch):
    from src.core.platform.common.exceptions import NotFoundError
    from src.core.platform.infrastructure.persistence.orm.master_data.org.org import OrganizationORM
    from src.core.platform.infrastructure.persistence.orm.tenant.tenancy.tenant import TenantORM

    catalog = services["module_catalog_service"]
    session = services["session"]
    recorded = _spy_recorded_events(catalog, monkeypatch)

    foreign_tenant_id = _unique_code("tenant-foreign")
    session.add(
        TenantORM(
            id=foreign_tenant_id, tenant_code=_unique_code("TF"), display_name="Foreign Tenant", is_active=True, version=1
        )
    )
    session.commit()
    foreign_org_id = _unique_code("org-foreign")
    session.add(
        OrganizationORM(
            id=foreign_org_id,
            tenant_id=foreign_tenant_id,
            organization_code=_unique_code("FOREIGN"),
            display_name="Foreign Org",
            is_enabled=True,
            version=1,
        )
    )
    session.commit()

    with pytest.raises(NotFoundError):
        catalog.disable_module(foreign_org_id, "project_management")

    assert recorded == []


# ---------------------------------------------------------------------------
# Provisioning / read-time seeding must not emit these events
# ---------------------------------------------------------------------------


def test_provisioning_new_organization_records_zero_module_events(services, monkeypatch):
    app_service = services["platform_runtime_application_service"]
    catalog = services["module_catalog_service"]
    recorded = _spy_recorded_events(catalog, monkeypatch)

    app_service.provision_organization(
        organization_code=_unique_code("PROV-NOEVT"),
        display_name="Provisioned No-Event Org",
        timezone_name="UTC",
        base_currency="EUR",
        is_enabled=False,
        initial_module_codes=["project_management"],
    )

    assert recorded == []


def test_read_time_default_seeding_records_zero_module_events(services, monkeypatch):
    organization_service = services["organization_service"]
    catalog = services["module_catalog_service"]
    new_org = organization_service.create_organization(
        organization_code=_unique_code("SEED-NOEVT"), display_name="Seed No-Event Org", is_enabled=False
    )
    recorded = _spy_recorded_events(catalog, monkeypatch)

    organization_service.enable_organization(new_org.id)
    services["tenant_context_service"].set_active_organization(new_org.id)
    catalog.list_entitlements()  # triggers _ensure_context_defaults' first-read row seeding

    assert recorded == []


# ---------------------------------------------------------------------------
# Rollback / commit-failure / post-commit isolation
# ---------------------------------------------------------------------------


def test_no_event_observable_on_commit_failure(services, monkeypatch):
    catalog = services["module_catalog_service"]
    org = services["tenant_context_service"].get_active_organization()

    bus = catalog._uow_factory._post_commit_bus
    seen = []
    for event_cls in (ModuleLicensed, ModuleLicenseRevoked, ModuleEnabled, ModuleDisabled, ModuleLifecycleTransitioned):
        bus.subscribe(event_cls, lambda e, c: seen.append(e))

    def _fail_commit(self):
        raise RuntimeError("simulated module entitlement commit failure")

    monkeypatch.setattr(SqlAlchemyModuleEntitlementUnitOfWork, "commit", _fail_commit)

    with pytest.raises(RuntimeError, match="simulated module entitlement commit failure"):
        catalog.disable_module(org.id, "project_management")

    assert seen == []
    # State unchanged -- the failed commit rolled back the entitlement write together with the
    # (never-observable) recorded event.
    assert catalog.get_entitlement("project_management").enabled is True


def test_one_post_commit_handler_failing_does_not_block_the_other_or_the_commit(services):
    catalog = services["module_catalog_service"]
    org = services["tenant_context_service"].get_active_organization()
    bus = catalog._uow_factory._post_commit_bus

    def _failing_handler(event, context):
        raise RuntimeError("simulated post-commit handler failure")

    healthy_seen = []
    bus.subscribe(ModuleDisabled, _failing_handler)
    bus.subscribe(ModuleDisabled, lambda e, c: healthy_seen.append(e))

    # Must not raise -- ISOLATE_AND_CONTINUE swallows the failing handler's exception.
    entitlement = catalog.disable_module(org.id, "project_management")

    assert entitlement.enabled is False
    assert len(healthy_seen) == 1
    reloaded = catalog.get_entitlement("project_management")
    assert reloaded.enabled is False


def test_post_commit_subscriber_receives_the_commands_own_domain_event_context(services):
    catalog = services["module_catalog_service"]
    org = services["tenant_context_service"].get_active_organization()
    bus = catalog._uow_factory._post_commit_bus
    seen = {}

    def _capture(event, context):
        seen["event"] = event
        seen["context"] = context

    bus.subscribe(ModuleEnabled, _capture)
    catalog.disable_module(org.id, "project_management")

    catalog.enable_module(org.id, "project_management")

    assert isinstance(seen["event"], ModuleEnabled)
    # Business fields only on the event -- execution metadata lives on the context, never
    # duplicated onto the event.
    assert not hasattr(seen["event"], "correlation_id")
    assert not hasattr(seen["event"], "causation_id")
    assert seen["context"].correlation_id is not None


# ---------------------------------------------------------------------------
# Exactly-once (no duplication from audit/legacy signal machinery)
# ---------------------------------------------------------------------------


def test_exactly_one_event_per_real_transition_no_duplication(services, monkeypatch):
    catalog = services["module_catalog_service"]
    org = services["tenant_context_service"].get_active_organization()
    recorded = _spy_recorded_events(catalog, monkeypatch)

    catalog.disable_module(org.id, "project_management")
    catalog.enable_module(org.id, "project_management")
    catalog.transition_module_lifecycle(org.id, "project_management", "trial")
    catalog.revoke_module_license(org.id, "project_management")
    catalog.license_module(org.id, "project_management")

    assert len(recorded) == 5
    assert [type(e) for e in recorded] == [
        ModuleDisabled,
        ModuleEnabled,
        ModuleLifecycleTransitioned,
        ModuleLicenseRevoked,
        ModuleLicensed,
    ]

