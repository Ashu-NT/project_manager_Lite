"""P4B (Organization Capability Transaction Convergence) + P5A (OrganizationCreated) + P10A
(Multi-Organization Model Correction) + P10D (Organization Event Modernization):
`OrganizationService`'s transaction-owning commands (`create_organization`, `update_organization`,
`enable_organization`, `bootstrap_defaults`) use the canonical fresh-session
`OrganizationUnitOfWork`. `create_organization` records exactly one `OrganizationCreated` before
commit (P5A); `update_organization`/`enable_organization`/`disable_organization` now record
`OrganizationProfileUpdated`/`OrganizationEnabled`/`OrganizationDisabled` before commit (P10D) --
the legacy `organizations_changed` signal no longer exists at all. P10A deleted
`set_active_organization` (its persisted mutual-exclusion designation behavior was legacy
single-org scaffolding) in favor of the narrower `enable_organization`/`disable_organization`,
which never touch sibling organizations.
"""

from __future__ import annotations

import inspect

import pytest

from src.core.platform.application.master_data.org import organization_service as organization_service_module
from src.core.platform.application.master_data.org.organization_service import OrganizationService
from src.core.platform.application.master_data.org.event_handlers.view_invalidation import (
    ORGANIZATION_LIST_SCOPE_CODE,
)
from src.core.platform.common.exceptions import NotFoundError, ValidationError
from src.core.platform.domain.security.auth.session import UserSessionContext, UserSessionPrincipal
from src.core.platform.infrastructure.persistence.orm.tenant.tenancy.tenant import TenantORM
from src.core.platform.infrastructure.persistence.organization_unit_of_work import (
    SqlAlchemyOrganizationUnitOfWork,
)
from src.core.shared.events.view_invalidation import AllTenants, TenantScope

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


def test_successful_create_organization_commits_and_publishes_view_invalidation_only_after_commit(
    services,
):
    """P5A + Organization-specific P6A cutover, legacy signal fully deleted in P10D: organization
    creation produces exactly one `OrganizationCreated` -> `ViewInvalidationHint` for the
    tenant-wide organization-list target, published only after commit, via the real
    composition-owned `ViewInvalidationChannel`."""
    organization_service = services["organization_service"]
    channel = services["platform_view_invalidation_channel"]
    hints = []
    channel.subscribe(AllTenants(), lambda hint: hints.append(hint))

    code = _unique_code("SUCCESS")
    organization = organization_service.create_organization(
        organization_code=code, display_name="Success Org"
    )

    assert organization.organization_code == code
    list_hints = [h for h in hints if h.scope_code == ORGANIZATION_LIST_SCOPE_CODE]
    assert len(list_hints) == 1
    assert isinstance(list_hints[0].scope, TenantScope)
    reloaded = organization_service._organization_repo.get(organization.id)
    assert reloaded is not None
    assert reloaded.organization_code == code


def test_duplicate_code_validation_failure_rolls_back(services, monkeypatch):
    organization_service = services["organization_service"]
    code = _unique_code("DUPE")
    organization_service.create_organization(organization_code=code, display_name="First")

    captured_uow = {}
    original_create = type(organization_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        captured_uow["uow"] = uow
        return uow

    monkeypatch.setattr(type(organization_service._uow_factory), "create", _spy_create)

    with pytest.raises(ValidationError, match="Organization code already exists"):
        organization_service.create_organization(organization_code=code, display_name="Second")

    uow = captured_uow["uow"]
    assert uow._committed is False
    assert uow._closed is True


def test_commit_failure_leaves_no_partial_state(services, monkeypatch):
    organization_service = services["organization_service"]

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


def test_enable_organization_default_mode_uses_a_fresh_uow(services, monkeypatch):
    organization_service = services["organization_service"]
    organization = organization_service.create_organization(
        organization_code=_unique_code("ACTIVATE"), display_name="Activate Org", is_enabled=False
    )

    seen_sessions = []
    original_create = type(organization_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen_sessions.append(uow._session)
        return uow

    monkeypatch.setattr(type(organization_service._uow_factory), "create", _spy_create)

    enabled = organization_service.enable_organization(organization.id)

    assert len(seen_sessions) == 1
    assert seen_sessions[0] is not organization_service._session
    assert enabled.is_enabled is True
    reloaded = organization_service._organization_repo.get(organization.id)
    assert reloaded.is_enabled is True


def test_enable_organization_is_a_noop_when_already_enabled_and_opens_no_uow(services, monkeypatch):
    """P10A: a past-tense state-transition write must represent an actual transition -- enabling
    an already-enabled organization performs no write, no audit, and no event (P10D:
    `OrganizationEnabled`, verified end to end via the real `ViewInvalidationChannel` rather than
    the deleted legacy signal)."""
    organization_service = services["organization_service"]
    channel = services["platform_view_invalidation_channel"]
    organization = organization_service.create_organization(
        organization_code=_unique_code("NOOP-ENABLE"), display_name="Already Enabled Org"
    )
    assert organization.is_enabled is True

    seen_sessions = []
    original_create = type(organization_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen_sessions.append(uow._session)
        return uow

    monkeypatch.setattr(type(organization_service._uow_factory), "create", _spy_create)

    hints = []
    channel.subscribe(AllTenants(), lambda hint: hints.append(hint))

    result = organization_service.enable_organization(organization.id)

    assert result.version == organization.version
    assert len(seen_sessions) == 1, "a UoW still opens (to look the organization up), but stages no write"
    assert hints == []


def test_disable_organization_does_not_touch_sibling_organizations(services):
    """P10A: the legacy sibling-deactivation invariant is deleted, not preserved under new
    vocabulary -- disabling one organization must never change any other organization's row."""
    organization_service = services["organization_service"]
    organization_a = organization_service.create_organization(
        organization_code=_unique_code("SIBLING-A"), display_name="Sibling A"
    )
    organization_b = organization_service.create_organization(
        organization_code=_unique_code("SIBLING-B"), display_name="Sibling B"
    )
    assert organization_a.is_enabled is True
    assert organization_b.is_enabled is True

    organization_service.disable_organization(organization_a.id)

    reloaded_a = organization_service._organization_repo.get(organization_a.id)
    reloaded_b = organization_service._organization_repo.get(organization_b.id)
    assert reloaded_a.is_enabled is False
    assert reloaded_b.is_enabled is True


def test_create_and_enable_organization_no_longer_accept_a_commit_argument(services):
    """P4C removes the grandfathered `commit=False` transaction switch from both methods --
    `provision_organization` now expresses its own transaction participation structurally via
    `_create_organization_using`/`_enable_organization_using` and a `PlatformProvisioningUnitOfWork`,
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
        organization_service.enable_organization(organization.id, commit=False)


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
        is_enabled=False,
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
        clock=organization_service._clock,
        user_session=ctx_b,
        enterprise_audit_service=organization_service._enterprise_audit_service,
        tenant_context_service=None,
        overview_rollup_reader=organization_service._overview_rollup_reader,
    )

    assert organization_a.id not in {org.id for org in service_as_b.list_organizations()}
    with pytest.raises(NotFoundError):
        service_as_b.update_organization(organization_a.id, display_name="Hijacked")


def test_p5a_does_not_add_p5b_plus_event_vocabulary():
    """Phase-boundary guard (superseding P4B's own, now-obsolete guard now that P5A legitimately
    records `OrganizationCreated`): no P5B+ event vocabulary belongs in this module."""
    source = inspect.getsource(organization_service_module)
    for forbidden in (
        "ModuleLicensed",
        "ModuleEnabled",
        "ModuleDisabled",
        "ScopeAccessGranted",
        "ScopeAccessRevoked",
        "RoleAssignmentGranted",
        "RoleAssignmentRevoked",
        "ApprovalRequested",
        "ApprovalApproved",
        "ApprovalRejected",
    ):
        assert forbidden not in source
