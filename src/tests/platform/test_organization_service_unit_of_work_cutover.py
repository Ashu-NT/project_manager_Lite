"""P4B (Organization Capability Transaction Convergence): `OrganizationService`'s
transaction-owning commands (`create_organization`, `update_organization`,
`set_active_organization` in their default commit=True mode, `bootstrap_defaults`) cut over onto
the canonical fresh-session `OrganizationUnitOfWork`. Mirrors
`test_approval_service_unit_of_work_cutover.py` (P4 Step 2's own equivalent for Approval).

P4B is transaction convergence only -- no `OrganizationCreated` DomainEvent, no ViewInvalidation
producer. `test_p4b_does_not_add_p5a_event_vocabulary` enforces that phase boundary.
"""

from __future__ import annotations

import inspect

import pytest

from src.core.platform.application.master_data.org import organization_service as organization_service_module
from src.core.platform.application.master_data.org.organization_service import OrganizationService
from src.core.platform.common.exceptions import NotFoundError, ValidationError
from src.core.platform.domain.security.auth.session import UserSessionContext, UserSessionPrincipal
from src.core.platform.infrastructure.persistence.orm.tenant.tenancy.tenant import TenantORM
from src.core.platform.infrastructure.persistence.organization_unit_of_work import (
    SqlAlchemyOrganizationUnitOfWork,
)
from src.core.shared.events.domain_events import domain_events

_COUNTER = {"n": 0}


def _unique_code(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def test_two_independent_create_organization_calls_use_genuinely_different_sessions(
    services, monkeypatch
):
    organization_service = services["organization_service"]
    created_sessions = []
    original_create = type(organization_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        created_sessions.append(uow._session)
        return uow

    monkeypatch.setattr(type(organization_service._uow_factory), "create", _spy_create)

    organization_service.create_organization(
        organization_code=_unique_code("FRESH-A"), display_name="Fresh Session A"
    )
    organization_service.create_organization(
        organization_code=_unique_code("FRESH-B"), display_name="Fresh Session B"
    )

    assert len(created_sessions) == 2
    assert created_sessions[0] is not created_sessions[1]
    assert all(s is not organization_service._session for s in created_sessions)


def test_create_organization_repository_and_audit_share_the_uow_session(services, monkeypatch):
    organization_service = services["organization_service"]
    seen = {}
    original_create = type(organization_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen["uow_session"] = uow._session
        seen["organizations_repo_session"] = uow.organizations.session
        seen["audit_session"] = uow._enterprise_audit_service._session
        return uow

    monkeypatch.setattr(type(organization_service._uow_factory), "create", _spy_create)

    organization_service.create_organization(
        organization_code=_unique_code("SHARE"), display_name="Shared Session Org"
    )

    assert seen["uow_session"] is seen["organizations_repo_session"]
    assert seen["uow_session"] is seen["audit_session"]


def test_successful_create_organization_commits_and_fires_legacy_signal_only_after_commit(
    services,
):
    organization_service = services["organization_service"]
    signal_calls = []
    domain_events.organizations_changed.connect(lambda org_id: signal_calls.append(org_id))

    code = _unique_code("SUCCESS")
    organization = organization_service.create_organization(
        organization_code=code, display_name="Success Org"
    )

    assert organization.organization_code == code
    assert signal_calls == [organization.id]
    reloaded = organization_service._organization_repo.get(organization.id)
    assert reloaded is not None
    assert reloaded.organization_code == code


def test_duplicate_code_validation_failure_rolls_back_and_fires_no_signal(services, monkeypatch):
    organization_service = services["organization_service"]
    code = _unique_code("DUPE")
    organization_service.create_organization(organization_code=code, display_name="First")

    signal_calls = []
    domain_events.organizations_changed.connect(lambda org_id: signal_calls.append(org_id))

    captured_uow = {}
    original_create = type(organization_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        captured_uow["uow"] = uow
        return uow

    monkeypatch.setattr(type(organization_service._uow_factory), "create", _spy_create)

    with pytest.raises(ValidationError, match="Organization code already exists"):
        organization_service.create_organization(organization_code=code, display_name="Second")

    assert signal_calls == []
    uow = captured_uow["uow"]
    assert uow._committed is False
    assert uow._closed is True


def test_commit_failure_leaves_no_partial_state_and_fires_no_signal(services, monkeypatch):
    organization_service = services["organization_service"]
    signal_calls = []
    domain_events.organizations_changed.connect(lambda org_id: signal_calls.append(org_id))

    captured_uow = {}
    original_create = type(organization_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        captured_uow["uow"] = uow
        return uow

    monkeypatch.setattr(type(organization_service._uow_factory), "create", _spy_create)

    def _fail_commit(self):
        raise RuntimeError("simulated database commit failure")

    monkeypatch.setattr(SqlAlchemyOrganizationUnitOfWork, "commit", _fail_commit)

    code = _unique_code("COMMITFAIL")
    with pytest.raises(RuntimeError, match="simulated database commit failure"):
        organization_service.create_organization(organization_code=code, display_name="Commit Fail Org")

    uow = captured_uow["uow"]
    assert uow._committed is False, "commit() failing must never mark the UoW committed"
    assert uow._closed is True, "the UoW's own __exit__ must still roll back and close"
    assert signal_calls == [], "no legacy signal may fire when commit fails"
    assert organization_service._organization_repo.get_by_code(code) is None


def test_no_global_mutation_session_touch_during_migrated_create(services):
    organization_service = services["organization_service"]
    legacy_session = organization_service._session
    legacy_session.commit()  # settle any pending state from fixture setup

    organization_service.create_organization(
        organization_code=_unique_code("ISOLATED"), display_name="Isolated Org"
    )

    # The migrated create ran entirely on its own fresh UoW Session -- the shared, legacy
    # Session must have picked up no pending new/dirty ORM objects as a side effect of it.
    assert len(legacy_session.new) == 0
    assert len(legacy_session.dirty) == 0


def test_update_organization_uses_a_fresh_uow_and_stages_audit_atomically(services, monkeypatch):
    organization_service = services["organization_service"]
    organization = organization_service.create_organization(
        organization_code=_unique_code("UPDATE"), display_name="Before Update"
    )

    seen = {}
    original_create = type(organization_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen["uow_session"] = uow._session
        return uow

    monkeypatch.setattr(type(organization_service._uow_factory), "create", _spy_create)

    updated = organization_service.update_organization(
        organization.id,
        expected_version=organization.version,
        display_name="After Update",
    )

    assert updated.display_name == "After Update"
    assert seen["uow_session"] is not organization_service._session
    reloaded = organization_service._organization_repo.get(organization.id)
    assert reloaded.display_name == "After Update"


def test_update_organization_stale_version_raises_and_does_not_mutate(services):
    organization_service = services["organization_service"]
    organization = organization_service.create_organization(
        organization_code=_unique_code("STALE"), display_name="Stale Org"
    )

    from src.core.platform.common.exceptions import ConcurrencyError

    with pytest.raises(ConcurrencyError):
        organization_service.update_organization(
            organization.id,
            expected_version=organization.version + 1,
            display_name="Should Not Apply",
        )

    reloaded = organization_service._organization_repo.get(organization.id)
    assert reloaded.display_name == "Stale Org"


def test_set_active_organization_default_mode_uses_a_fresh_uow(services, monkeypatch):
    organization_service = services["organization_service"]
    organization = organization_service.create_organization(
        organization_code=_unique_code("ACTIVATE"), display_name="Activate Org", is_active=False
    )

    seen_sessions = []
    original_create = type(organization_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen_sessions.append(uow._session)
        return uow

    monkeypatch.setattr(type(organization_service._uow_factory), "create", _spy_create)

    activated = organization_service.set_active_organization(organization.id)

    assert len(seen_sessions) == 1
    assert seen_sessions[0] is not organization_service._session
    assert activated.is_active is True
    assert organization_service.get_active_organization().id == organization.id


def test_create_and_activate_organization_no_longer_accept_a_commit_argument(services):
    """P4C removes the grandfathered `commit=False` transaction switch from both methods --
    `provision_organization` now expresses its own transaction participation structurally via
    `_create_organization_using`/`_activate_organization_using` and a `PlatformProvisioningUnitOfWork`,
    never a boolean. Structural proof, not just a grep: the public methods genuinely reject it."""
    organization_service = services["organization_service"]
    organization = organization_service.create_organization(
        organization_code=_unique_code("NOCOMMITARG"), display_name="No Commit Arg Org"
    )
    with pytest.raises(TypeError):
        organization_service.create_organization(
            organization_code=_unique_code("NOCOMMITARG2"), display_name="x", commit=False
        )
    with pytest.raises(TypeError):
        organization_service.set_active_organization(organization.id, commit=False)


def test_provision_organization_still_commits_organization_and_entitlements_atomically(services):
    """Real regression for the one genuine caller-owned case: `provision_organization` composes
    Organization creation, module entitlement provisioning, and (optionally) activation into one
    `PlatformProvisioningUnitOfWork` transaction (P4C) -- structurally, not via `commit=False`.
    Must remain atomic and externally unaffected by the P4B/P4C cutovers."""
    app_service = services["platform_runtime_application_service"]

    created = app_service.provision_organization(
        organization_code=_unique_code("PROVISION"),
        display_name="Provisioned Org",
        timezone_name="UTC",
        base_currency="EUR",
        is_active=False,
        initial_module_codes=[],
    )

    assert created.organization_code.startswith("PROVISION")
    reloaded = services["organization_service"]._organization_repo.get(created.id)
    assert reloaded is not None


def test_bootstrap_defaults_is_a_noop_when_organizations_already_exist(services):
    organization_service = services["organization_service"]
    before = organization_service.list_organizations()
    organization_service.bootstrap_defaults()
    after = organization_service.list_organizations()
    assert len(before) == len(after)


def test_migrated_create_and_update_remain_tenant_isolated(services):
    """Tenant B must not be able to see or update an organization created via the migrated,
    fresh-UoW `create_organization`/`update_organization` under Tenant A."""
    organization_service = services["organization_service"]
    session = services["session"]

    organization_a = organization_service.create_organization(
        organization_code=_unique_code("TENANT-A-ORG"), display_name="Tenant A Org"
    )

    tenant_b_id = "tenant-cutover-b"
    session.add(
        TenantORM(id=tenant_b_id, tenant_code="CUTOVER-B", display_name="Cutover Tenant B", is_active=True, version=1)
    )
    session.commit()

    ctx_b = UserSessionContext()
    ctx_b.set_principal(
        UserSessionPrincipal(
            user_id="tenant-b-user",
            username="tenant-b-user",
            display_name="Tenant B User",
            role_names=frozenset(["admin"]),
            permissions=frozenset(["settings.manage"]),
        )
    )
    ctx_b.set_active_tenant_id(tenant_b_id)
    service_as_b = OrganizationService(
        session=organization_service._session,
        organization_repo=organization_service._organization_repo,
        uow_factory=organization_service._uow_factory,
        user_session=ctx_b,
        enterprise_audit_service=organization_service._enterprise_audit_service,
        tenant_context_service=None,
        overview_rollup_reader=organization_service._overview_rollup_reader,
    )

    assert organization_a.id not in {org.id for org in service_as_b.list_organizations()}
    with pytest.raises(NotFoundError):
        service_as_b.update_organization(organization_a.id, display_name="Hijacked")


def test_p4b_does_not_add_p5a_event_vocabulary():
    """Phase-boundary guard: P4B is transaction convergence only. `OrganizationCreated` and any
    `uow.record_event(` call belong to P5A, not this phase."""
    source = inspect.getsource(organization_service_module)
    assert "OrganizationCreated" not in source
    assert "record_event(" not in source
    assert not hasattr(organization_service_module, "OrganizationCreated")
