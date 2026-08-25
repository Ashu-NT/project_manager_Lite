"""P5B prerequisite (Module Entitlement Transaction Convergence): the generic
`ModuleCatalogService.set_module_state` cut over from the shared, process-lifetime Session onto a
canonical, fresh-session `ModuleEntitlementUnitOfWork`, and from an ambient
(active-organization-only) scope onto an explicit `organization_id` parameter that can target ANY
organization within the caller's authenticated tenant -- not only the currently active one.
Mirrors `test_organization_service_unit_of_work_cutover.py` (P4B's own equivalent for
Organization).

P5B-SEM/P5B-1 then retired `set_module_state` itself in favor of five explicit business commands
(`license_module`/`revoke_module_license`/`enable_module`/`disable_module`/
`transition_module_lifecycle`) -- this file now exercises the same transaction/scope guarantees
through those commands (using `disable_module` as the representative single-field mutation).

This phase is transaction/scope convergence only -- no `ModuleLicensed`/`ModuleEnabled`/
`ModuleDisabled`/`ModuleLicenseGranted`/`ModuleLicenseRevoked`/`ModuleLifecycleTransitioned`
DomainEvent, no ViewInvalidation producer, per the P5B/P5B-SEM reports' own findings.
`test_module_entitlement_prerequisite_does_not_add_event_vocabulary` enforces that phase boundary.
"""

from __future__ import annotations

import inspect

import pytest

from src.core.platform.common.exceptions import ValidationError
from src.core.platform.infrastructure.persistence.module_entitlement_unit_of_work import (
    SqlAlchemyModuleEntitlementUnitOfWork,
)

_COUNTER = {"n": 0}


def _unique_code(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def test_fresh_session_per_module_command_call(services, monkeypatch):
    module_catalog = services["module_catalog_service"]
    active_org = services["organization_service"].get_active_organization()
    seen_sessions = []
    original_create = type(module_catalog._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen_sessions.append(uow._session)
        return uow

    monkeypatch.setattr(type(module_catalog._uow_factory), "create", _spy_create)

    module_catalog.disable_module(active_org.id, "project_management")
    module_catalog.enable_module(active_org.id, "project_management")

    assert len(seen_sessions) == 2
    assert seen_sessions[0] is not seen_sessions[1]
    assert all(s is not services["session"] for s in seen_sessions)


def test_repository_and_audit_share_the_uow_session(services, monkeypatch):
    module_catalog = services["module_catalog_service"]
    active_org = services["organization_service"].get_active_organization()
    seen = {}
    original_create = type(module_catalog._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen["uow_session"] = uow._session
        seen["entitlements_repo_session"] = uow.entitlements.session
        seen["audit_session"] = uow._enterprise_audit_service._session
        return uow

    monkeypatch.setattr(type(module_catalog._uow_factory), "create", _spy_create)

    module_catalog.disable_module(active_org.id, "project_management")

    assert seen["uow_session"] is seen["entitlements_repo_session"]
    assert seen["uow_session"] is seen["audit_session"]


def test_audit_entry_is_atomic_with_the_entitlement_write(services, monkeypatch):
    """P5B prerequisite fix (preserved through P5B-SEM's command refactor): the entitlement
    write and its audit entry share one fresh UoW Session -- a commit failure rolls back both
    together (proven structurally: the UoW's own `_committed`/`_closed` state)."""
    module_catalog = services["module_catalog_service"]
    active_org = services["organization_service"].get_active_organization()
    captured_uow = {}
    original_create = type(module_catalog._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        captured_uow["uow"] = uow
        return uow

    monkeypatch.setattr(type(module_catalog._uow_factory), "create", _spy_create)

    def _fail_commit(self):
        raise RuntimeError("simulated module entitlement commit failure")

    monkeypatch.setattr(SqlAlchemyModuleEntitlementUnitOfWork, "commit", _fail_commit)

    with pytest.raises(RuntimeError, match="simulated module entitlement commit failure"):
        module_catalog.disable_module(active_org.id, "project_management")

    uow = captured_uow["uow"]
    assert uow._committed is False
    assert uow._closed is True
    # The entitlement must still read as enabled (unchanged) -- the failed commit rolled back
    # both the entitlement row and its audit entry together.
    entitlement = module_catalog.get_entitlement("project_management")
    assert entitlement.enabled is True


def test_no_global_mutation_session_touch(services):
    module_catalog = services["module_catalog_service"]
    active_org = services["organization_service"].get_active_organization()
    legacy_session = services["session"]
    legacy_session.commit()

    module_catalog.disable_module(active_org.id, "project_management")

    assert len(legacy_session.new) == 0
    assert len(legacy_session.dirty) == 0


def test_organization_id_is_required_and_explicit(services):
    module_catalog = services["module_catalog_service"]
    with pytest.raises(ValidationError, match="Organization context is required"):
        module_catalog.disable_module("", "project_management")
    with pytest.raises(TypeError):
        module_catalog.disable_module()  # organization_id/module_code are positional-required


def test_non_active_organization_mutation_affects_only_that_organization(services):
    """Mandatory P5B prerequisite test: mutating a NON-active organization's module entitlement
    must succeed and affect only that organization, without changing which organization is
    active first -- structurally impossible before this convergence (the old `upsert()` path
    required the active organization to match, via `TenantScopedRepositorySupport`)."""
    organization_service = services["organization_service"]
    module_catalog = services["module_catalog_service"]

    org_a1 = organization_service.get_active_organization()
    org_a2 = organization_service.create_organization(
        organization_code=_unique_code("NONACTIVE"), display_name="Non-Active Org A2", is_active=False
    )
    assert organization_service.get_active_organization().id == org_a1.id

    entitlement_a2 = module_catalog.disable_module(org_a2.id, "project_management")
    assert entitlement_a2.enabled is False

    # A1 (still active throughout -- never switched) must be completely unaffected.
    assert organization_service.get_active_organization().id == org_a1.id
    entitlement_a1 = module_catalog.get_entitlement("project_management")
    assert entitlement_a1.enabled is True

    # Read back A2's own state explicitly (never via the ambient active-org read path, which
    # would incorrectly read A1's state) -- proves the write really landed on A2, not A1.
    with module_catalog._uow_factory.create(context=module_catalog._new_context()) as uow:
        a2_record = uow.entitlements.get_for_organization_in_tenant(org_a2.id, "project_management")
        # Read-only -- clean exit without commit() triggers the UoW's own documented safety-net
        # rollback-and-close, which is a no-op here since nothing was written.
    assert a2_record is not None
    assert a2_record.enabled is False


def test_module_entitlement_prerequisite_does_not_add_event_vocabulary():
    """Phase-boundary guard: transaction/scope convergence (P5B) and the semantic command
    refactor (P5B-SEM/P5B-1) are both event-free. No DomainEvent class name, no `uow.record_event(`
    call, exists anywhere in the Module Entitlement capability yet."""
    for module_name in ("module_catalog_service", "module_catalog_mutation", "module_catalog_context"):
        module = __import__(
            f"src.core.platform.application.tenant.modules.{module_name}", fromlist=[module_name]
        )
        source = inspect.getsource(module)
        for forbidden in (
            "ModuleLicensed",
            "ModuleLicenseGranted",
            "ModuleLicenseRevoked",
            "ModuleEnabled",
            "ModuleDisabled",
            "ModuleLifecycleTransitioned",
            "record_event(",
        ):
            assert forbidden not in source
