"""P4C (Platform Runtime Organization Provisioning Transaction Convergence):
`PlatformRuntimeApplicationService.provision_organization` cut over from the legacy,
process-lifetime shared-Session transaction onto a canonical, fresh-session
`PlatformProvisioningUnitOfWork`. Mirrors `test_organization_service_unit_of_work_cutover.py`/
`test_approval_service_unit_of_work_cutover.py`'s own equivalents.

P4C is transaction convergence only -- no `OrganizationCreated`/`ModuleLicensed`/`ModuleEnabled`/
`ModuleDisabled` DomainEvent, no ViewInvalidation producer.
`test_p4c_does_not_add_p5a_event_vocabulary` enforces that phase boundary.
"""

from __future__ import annotations

import inspect

import pytest

from src.core.platform.application.platform_runtime import platform_runtime_service as platform_runtime_service_module
from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.infrastructure.persistence.platform_provisioning_unit_of_work import (
    SqlAlchemyPlatformProvisioningUnitOfWork,
)
from src.core.shared.events.domain_events import domain_events

_COUNTER = {"n": 0}


def _unique_code(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def test_successful_provisioning_persists_organization_and_entitlements_atomically_via_fresh_uow(
    services,
):
    app_service = services["platform_runtime_application_service"]
    organization_service = services["organization_service"]

    code = _unique_code("SUCCESS-PROV")
    organization = app_service.provision_organization(
        organization_code=code,
        display_name="Success Provisioned Org",
        timezone_name="UTC",
        base_currency="EUR",
        is_active=False,
        initial_module_codes=["project_management"],
    )

    reloaded = organization_service._organization_repo.get(organization.id)
    assert reloaded is not None
    assert reloaded.organization_code == code
    # Entitlement rows proven durable via the service surface: activating the provisioned
    # organization must reflect the module it was provisioned with.
    module_catalog = services["module_catalog_service"]
    organization_service.set_active_organization(organization.id)
    assert module_catalog.is_enabled("project_management") is True


def test_fresh_session_per_provisioning_call(services, monkeypatch):
    app_service = services["platform_runtime_application_service"]
    seen_sessions = []
    original_create = type(app_service._provisioning_uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen_sessions.append(uow._session)
        return uow

    monkeypatch.setattr(type(app_service._provisioning_uow_factory), "create", _spy_create)

    app_service.provision_organization(
        organization_code=_unique_code("FRESH-A"), display_name="Fresh A", timezone_name="UTC",
        base_currency="EUR", is_active=False, initial_module_codes=[],
    )
    app_service.provision_organization(
        organization_code=_unique_code("FRESH-B"), display_name="Fresh B", timezone_name="UTC",
        base_currency="EUR", is_active=False, initial_module_codes=[],
    )

    assert len(seen_sessions) == 2
    assert seen_sessions[0] is not seen_sessions[1]


def test_provisioning_participants_share_the_same_uow_session(services, monkeypatch):
    app_service = services["platform_runtime_application_service"]
    seen = {}
    original_create = type(app_service._provisioning_uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen["uow_session"] = uow._session
        seen["organizations_repo_session"] = uow.organizations.session
        seen["entitlements_repo_session"] = uow.entitlements.session
        seen["audit_session"] = uow._enterprise_audit_service._session
        return uow

    monkeypatch.setattr(type(app_service._provisioning_uow_factory), "create", _spy_create)

    app_service.provision_organization(
        organization_code=_unique_code("SHARE-PROV"), display_name="Shared Session Prov",
        timezone_name="UTC", base_currency="EUR", is_active=False, initial_module_codes=["project_management"],
    )

    assert seen["uow_session"] is seen["organizations_repo_session"]
    assert seen["uow_session"] is seen["entitlements_repo_session"]
    assert seen["uow_session"] is seen["audit_session"]


def test_no_global_session_touch_during_provisioning(services):
    app_service = services["platform_runtime_application_service"]
    legacy_session = services["session"]
    legacy_session.commit()  # settle any pending fixture-setup state

    app_service.provision_organization(
        organization_code=_unique_code("ISOLATED-PROV"), display_name="Isolated Prov",
        timezone_name="UTC", base_currency="EUR", is_active=False, initial_module_codes=[],
    )

    assert len(legacy_session.new) == 0
    assert len(legacy_session.dirty) == 0


def test_late_step_failure_rolls_back_organization_and_entitlements_together(services):
    """A failure in a later provisioning step (an unknown module code, raised from module
    entitlement provisioning) must roll back the ALREADY-staged organization row too -- proving
    the two writes share one transaction, not two."""
    app_service = services["platform_runtime_application_service"]
    organization_service = services["organization_service"]
    code = _unique_code("LATEFAIL")

    with pytest.raises(NotFoundError):
        app_service.provision_organization(
            organization_code=code,
            display_name="Late Failure Org",
            timezone_name="UTC",
            base_currency="EUR",
            is_active=False,
            initial_module_codes=["definitely-not-a-real-module-code"],
        )

    assert organization_service._organization_repo.get_by_code(code) is None


def test_commit_failure_leaves_no_partial_provisioning_state(services, monkeypatch):
    app_service = services["platform_runtime_application_service"]
    organization_service = services["organization_service"]
    signal_calls = []
    domain_events.organizations_changed.connect(lambda org_id: signal_calls.append(org_id))

    captured_uow = {}
    original_create = type(app_service._provisioning_uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        captured_uow["uow"] = uow
        return uow

    monkeypatch.setattr(type(app_service._provisioning_uow_factory), "create", _spy_create)

    def _fail_commit(self):
        raise RuntimeError("simulated provisioning commit failure")

    monkeypatch.setattr(SqlAlchemyPlatformProvisioningUnitOfWork, "commit", _fail_commit)

    code = _unique_code("COMMITFAIL-PROV")
    with pytest.raises(RuntimeError, match="simulated provisioning commit failure"):
        app_service.provision_organization(
            organization_code=code, display_name="Commit Fail Prov", timezone_name="UTC",
            base_currency="EUR", is_active=False, initial_module_codes=[],
        )

    uow = captured_uow["uow"]
    assert uow._committed is False
    assert uow._closed is True
    assert signal_calls == []
    assert organization_service._organization_repo.get_by_code(code) is None


def test_runtime_active_organization_context_changes_only_after_successful_commit(services):
    app_service = services["platform_runtime_application_service"]
    tenant_context_service = services["tenant_context_service"]
    default_active_id = tenant_context_service.get_active_organization().id

    code = _unique_code("ACTIVATE-PROV")
    organization = app_service.provision_organization(
        organization_code=code, display_name="Activate Prov Org", timezone_name="UTC",
        base_currency="EUR", is_active=True, initial_module_codes=[],
    )

    assert tenant_context_service.get_active_organization().id == organization.id
    assert organization.id != default_active_id


def test_provisioning_remains_tenant_scoped(services):
    app_service = services["platform_runtime_application_service"]
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    tenant_id = tenant_context_service.get_active_tenant_id()

    code = _unique_code("TENANT-PROV")
    organization = app_service.provision_organization(
        organization_code=code, display_name="Tenant Prov Org", timezone_name="UTC",
        base_currency="EUR", is_active=False, initial_module_codes=[],
    )

    reloaded = organization_service._organization_repo.get_for_tenant(organization.id, tenant_id)
    assert reloaded is not None


def test_p4c_does_not_add_p5a_event_vocabulary():
    """Phase-boundary guard: P4C is transaction convergence only. `OrganizationCreated`,
    `ModuleLicensed`/`ModuleEnabled`/`ModuleDisabled`, and any `uow.record_event(` call belong to
    P5A/P5B, not this phase."""
    source = inspect.getsource(platform_runtime_service_module)
    for forbidden in ("OrganizationCreated", "ModuleLicensed", "ModuleEnabled", "ModuleDisabled", "record_event("):
        assert forbidden not in source
