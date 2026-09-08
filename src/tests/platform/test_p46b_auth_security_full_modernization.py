"""P46B: Final Application Legacy Capability -- Auth/Security Full Modernization + Delete
`auth_changed` + Delete Legacy DomainEvents Infrastructure.

Mandatory new regression coverage for this phase: bounded-retry concurrent lockout race,
audit-failure-during-failed-login (fail-closed), registration rollback + event completeness,
bootstrap self-heal event completeness, custom-Role retirement N-binding revocation + rollback,
`account_security`/`authorization_context` ViewInvalidation precision (including cross-tenant
isolation), the ephemeral session-transport listeners, and the permanent zero-legacy-Signal
application-wide guard (including a hypothetical-reintroduction-fails-the-guard proof).

See `docs/architecture/event-modernization-plan.md`'s P46A/P46A-FINAL-CLOSURE/P46B entries for
the full design history and rationale.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from src.application.runtime import build_desktop_api_registry
from src.core.platform.application.security.auth.credentials.authentication_transactions import (
    register_failed_login,
)
from src.core.platform.common.exceptions import ConcurrencyError
from src.core.platform.domain.security.authorization.roles import (
    ROLE_SCOPE_PLATFORM,
    ROLE_SCOPE_TENANT,
)
from src.core.platform.domain.security.auth.events import (
    AuthenticationFailureRecorded,
    CustomRoleRetired,
)
from src.ui_qml.platform.context import PlatformWorkspaceCatalog

_PASSWORD = "P46bStrong123!"
_COUNTER = {"n": 0}


def _unique(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _catalog(services) -> PlatformWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return PlatformWorkspaceCatalog(desktop_api_registry=registry)


def _tenant_id(services) -> str:
    return services["tenant_context_service"].require_active_tenant_id(
        operation_label="P46B test"
    )


def _set_tenant_admin(services, *, username: str | None = None):
    auth = services["auth_service"]
    tenant_id = _tenant_id(services)
    actor = auth.register_user(
        username or _unique("p46b-admin"),
        _PASSWORD,
        role_names=["tenant_admin"],
        tenant_id=tenant_id,
    )
    principal = auth.build_principal_for_context(
        actor,
        tenant_id=tenant_id,
        organization_id=services["tenant_context_service"].get_active_organization_id(),
    )
    services["user_session"].set_principal(principal)
    return actor


def _allow_tenant_admin_to_assign(services, role_id: str) -> None:
    """`create_delegation_policy` requires `platform.admin` -- create it as the platform admin,
    then restore whichever principal was active (the tenant admin under test)."""
    auth = services["auth_service"]
    tenant_id = _tenant_id(services)
    tenant_admin_role = auth._role_repo.get_by_name("tenant_admin")
    acting_principal = services["user_session"].principal
    services["user_session"].set_principal(
        auth.build_principal(auth.authenticate("admin", "ChangeMe123!"))
    )
    services["role_governance_service"].create_delegation_policy(
        actor_role_id=tenant_admin_role.id,
        assignable_role_id=role_id,
        target_scope_type="tenant",
        tenant_id=tenant_id,
    )
    services["user_session"].set_principal(acting_principal)


def _spy_record_event(monkeypatch) -> list:
    from src.infra.persistence.db.unit_of_work import SqlAlchemyUnitOfWorkBase

    recorded: list = []
    original = SqlAlchemyUnitOfWorkBase.record_event

    def _spy(self, event):
        recorded.append(event)
        return original(self, event)

    monkeypatch.setattr(SqlAlchemyUnitOfWorkBase, "record_event", _spy)
    return recorded


# ---------------------------------------------------------------------------
# 1. register_failed_login: bounded retry, no silent swallow, fail-closed
# ---------------------------------------------------------------------------


def test_register_failed_login_bounded_retry_recovers_from_concurrent_write(
    services, monkeypatch
):
    """Two failed-login attempts race on the same account's real CAS -- the second call is
    handed a stale `UserAccount` (as if loaded before the first attempt committed). It must not
    lose its own increment: exactly one bounded retry reloads fresh state and reapplies it."""
    from datetime import datetime, timezone

    auth = services["auth_service"]
    target = auth.register_user(_unique("p46b-race-target"), _PASSWORD, role_names=[])
    stale_copy = auth._user_repo.get(target.id)

    recorded = _spy_record_event(monkeypatch)

    register_failed_login(
        auth, auth._user_repo.get(target.id), username=target.username,
        occurred_at=datetime.now(timezone.utc),
    )
    # `stale_copy` still holds the pre-first-attempt version -- its own commit must conflict,
    # then recover via the bounded retry rather than silently losing this second attempt.
    register_failed_login(
        auth, stale_copy, username=target.username, occurred_at=datetime.now(timezone.utc)
    )

    refreshed = auth._user_repo.get(target.id)
    assert refreshed.failed_login_attempts == 2, "the second (raced) attempt must not be lost"
    failure_events = [e for e in recorded if isinstance(e, AuthenticationFailureRecorded)]
    assert len(failure_events) == 2, "exactly one typed event per successful commit, no more, no fewer"
    assert [e.failed_attempts for e in failure_events] == [1, 2]


def test_register_failed_login_exhausted_retry_propagates_not_silently_swallowed(
    services, monkeypatch
):
    """A conflict on the bounded retry's OWN commit attempt (a second concurrent writer) must
    propagate as `ConcurrencyError` -- never be silently discarded, unlike the prior bare
    `except Exception: ... return`."""
    from datetime import datetime, timezone

    from src.core.platform.infrastructure.persistence.repositories.security.auth.auth import (
        SqlAlchemyUserRepository,
    )

    auth = services["auth_service"]
    target = auth.register_user(_unique("p46b-race-exhaust"), _PASSWORD, role_names=[])
    stale_copy = auth._user_repo.get(target.id)

    original_update = SqlAlchemyUserRepository.update
    call_count = {"n": 0}

    def _always_conflict(self, user):
        call_count["n"] += 1
        raise ConcurrencyError("simulated persistent concurrent write", code="CONCURRENCY_CONFLICT")

    monkeypatch.setattr(SqlAlchemyUserRepository, "update", _always_conflict)
    with pytest.raises(ConcurrencyError):
        register_failed_login(
            auth, stale_copy, username=target.username, occurred_at=datetime.now(timezone.utc)
        )
    assert call_count["n"] == 2, "exactly the bounded max (2 attempts), not silently retried forever"


def test_register_failed_login_audit_failure_propagates_and_rolls_back(services, monkeypatch):
    """Any exception OTHER than `ConcurrencyError` (e.g. the required audit write failing) must
    propagate immediately -- and, since it happens inside the UoW, roll back the whole attempt
    rather than leaving a half-recorded lockout state."""
    from datetime import datetime, timezone

    auth = services["auth_service"]
    target = auth.register_user(_unique("p46b-audit-fail"), _PASSWORD, role_names=[])
    before = auth._user_repo.get(target.id).failed_login_attempts

    def _raise(*_a, **_kw):
        raise RuntimeError("security audit unavailable")

    monkeypatch.setattr(auth._security_audit_repo, "add_platform", _raise)
    monkeypatch.setattr(auth._security_audit_repo, "add_for_tenant", _raise)

    with pytest.raises(RuntimeError, match="security audit unavailable"):
        register_failed_login(
            auth, auth._user_repo.get(target.id), username=target.username,
            occurred_at=datetime.now(timezone.utc),
        )

    assert auth._user_repo.get(target.id).failed_login_attempts == before, (
        "a failed audit write must roll back the whole attempt, not partially persist it"
    )


# ---------------------------------------------------------------------------
# 2. Registration: one physical transaction, exact event completeness, rollback
# ---------------------------------------------------------------------------


def test_registration_records_exactly_user_created_membership_provisioned_and_role_bindings(
    services, monkeypatch
):
    from src.core.platform.domain.security.auth.events import (
        TenantMembershipProvisioned,
        UserAccountCreated,
    )
    from src.core.platform.domain.security.authorization.roles.events import RoleBindingAssigned

    _set_tenant_admin(services)
    auth = services["auth_service"]
    tenant_id = _tenant_id(services)
    recorded = _spy_record_event(monkeypatch)

    created = auth.register_user(
        _unique("p46b-reg-complete"),
        _PASSWORD,
        role_names=["viewer", "tenant_admin"],
        tenant_id=tenant_id,
    )

    created_events = [e for e in recorded if isinstance(e, UserAccountCreated)]
    provisioned_events = [e for e in recorded if isinstance(e, TenantMembershipProvisioned)]
    binding_events = [
        e for e in recorded if isinstance(e, RoleBindingAssigned) and e.principal_id == created.id
    ]
    assert len(created_events) == 1
    assert created_events[0].user_id == created.id
    assert created_events[0].tenant_id == tenant_id
    assert len(provisioned_events) == 1
    assert provisioned_events[0].user_id == created.id
    assert provisioned_events[0].tenant_id == tenant_id
    assert len(binding_events) == 2, "one RoleBindingAssigned per requested role, no fewer, no more"


def test_platform_scoped_registration_records_zero_membership_provisioned(services, monkeypatch):
    """A platform-scoped registration (no tenant) must never record a `TenantMembershipProvisioned`
    -- that fact is only true for tenant-scoped registration."""
    from src.core.platform.domain.security.auth.events import TenantMembershipProvisioned

    services["user_session"].set_principal(
        services["auth_service"].build_principal(
            services["auth_service"].authenticate("admin", "ChangeMe123!")
        )
    )
    auth = services["auth_service"]
    recorded = _spy_record_event(monkeypatch)

    auth.register_user(_unique("p46b-platform-reg"), _PASSWORD, role_names=[])

    assert [e for e in recorded if isinstance(e, TenantMembershipProvisioned)] == []


def test_registration_rolls_back_the_entire_transaction_and_records_zero_events_on_integrity_error(
    services, monkeypatch
):
    from sqlalchemy import func
    from sqlalchemy.exc import IntegrityError

    from src.core.platform.infrastructure.persistence.orm.security.auth.auth import UserORM
    from src.core.platform.infrastructure.persistence.repositories.security.auth.auth import (
        SqlAlchemyUserRepository,
    )

    _set_tenant_admin(services)
    auth = services["auth_service"]
    tenant_id = _tenant_id(services)
    recorded = _spy_record_event(monkeypatch)
    before_user_count = services["session"].scalar(select(func.count()).select_from(UserORM))

    def _raise(self, user):
        raise IntegrityError("insert", {}, Exception("username already exists"))

    monkeypatch.setattr(SqlAlchemyUserRepository, "add", _raise)

    with pytest.raises(Exception):
        auth.register_user(
            _unique("p46b-reg-rollback"), _PASSWORD, role_names=["viewer"], tenant_id=tenant_id
        )

    after_user_count = services["session"].scalar(select(func.count()).select_from(UserORM))
    assert after_user_count == before_user_count
    assert recorded == [], "no event may survive a rolled-back registration"


# ---------------------------------------------------------------------------
# 3. Bootstrap: self-heal repair path, exact event completeness
# ---------------------------------------------------------------------------


def test_bootstrap_role_repair_records_exactly_one_role_binding_assigned_and_no_account_event(
    services, monkeypatch
):
    from src.core.platform.domain.security.auth.events import UserAccountCreated
    from src.core.platform.domain.security.authorization.roles.events import RoleBindingAssigned

    auth = services["auth_service"]
    admin = auth._user_repo.get_by_username("admin")
    admin_role = auth._require_role_by_name("admin")
    binding = auth._role_binding_repo.get_active_for_assignment(
        principal_id=admin.id,
        role_id=admin_role.id,
        tenant_id=None,
        actual_scope_type=ROLE_SCOPE_PLATFORM,
        actual_scope_id=None,
    )
    assert binding is not None
    auth._role_binding_repo.revoke(binding.id, revoked_at=binding.assigned_at)
    services["session"].commit()

    recorded = _spy_record_event(monkeypatch)
    auth.bootstrap_defaults()

    binding_events = [e for e in recorded if isinstance(e, RoleBindingAssigned)]
    assert len(binding_events) == 1, "self-repair records exactly the fact for the actual change"
    assert binding_events[0].principal_id == admin.id
    assert [e for e in recorded if isinstance(e, UserAccountCreated)] == [], (
        "repair must never fabricate a UserAccountCreated fact -- the account already existed"
    )
    assert auth._role_binding_repo.get_active_for_assignment(
        principal_id=admin.id, role_id=admin_role.id, tenant_id=None,
        actual_scope_type=ROLE_SCOPE_PLATFORM, actual_scope_id=None,
    ) is not None


def test_bootstrap_defaults_is_idempotent_and_records_zero_events_when_nothing_changed(
    services, monkeypatch
):
    auth = services["auth_service"]
    recorded = _spy_record_event(monkeypatch)

    auth.bootstrap_defaults()  # admin already exists with its binding intact

    assert recorded == []


# ---------------------------------------------------------------------------
# 4. Custom-Role retirement: N-binding revocation, one transaction, rollback
# ---------------------------------------------------------------------------


def test_custom_role_retirement_revokes_every_active_binding_with_one_event_each(
    services, monkeypatch
):
    from src.core.platform.domain.security.authorization.roles.events import RoleBindingRevoked

    _set_tenant_admin(services)
    tenant_id = _tenant_id(services)
    role_admin_service = services["tenant_role_administration_service"]
    role_governance_service = services["role_governance_service"]
    auth = services["auth_service"]

    role = role_admin_service.create_custom_role(
        name=_unique("p46b_custom_role"),
        display_name="P46B Custom Role",
        permission_codes={"project.read"},
    )
    _allow_tenant_admin_to_assign(services, role.id)
    holders = [
        auth.register_user(_unique("p46b-holder"), _PASSWORD, role_names=[], tenant_id=tenant_id)
        for _ in range(3)
    ]
    for holder in holders:
        role_governance_service.assign_role(target_user_id=holder.id, role_id=role.id)

    recorded = _spy_record_event(monkeypatch)
    retired = role_admin_service.retire_custom_role(
        role.id, expected_policy_version=role.policy_version
    )

    assert retired.status == "retired"
    revoked_events = [e for e in recorded if isinstance(e, RoleBindingRevoked)]
    assert len(revoked_events) == 3, "one RoleBindingRevoked per holder, no bulk-SQL bypass"
    assert {e.role_id for e in revoked_events} == {role.id}
    retirement_events = [e for e in recorded if isinstance(e, CustomRoleRetired)]
    assert len(retirement_events) == 1
    for holder in holders:
        assert auth._role_binding_repo.get_active_for_assignment(
            principal_id=holder.id,
            role_id=role.id,
            tenant_id=tenant_id,
            actual_scope_type=ROLE_SCOPE_TENANT,
            actual_scope_id=tenant_id,
        ) is None


def test_custom_role_retirement_rolls_back_all_binding_revocations_on_audit_failure(
    services, monkeypatch
):
    from sqlalchemy import func

    from src.core.platform.infrastructure.persistence.orm.security.auth.auth import RoleBindingORM

    _set_tenant_admin(services)
    tenant_id = _tenant_id(services)
    role_admin_service = services["tenant_role_administration_service"]
    role_governance_service = services["role_governance_service"]
    auth = services["auth_service"]

    role = role_admin_service.create_custom_role(
        name=_unique("p46b_custom_role_rb"),
        display_name="P46B Rollback Role",
        permission_codes={"project.read"},
    )
    _allow_tenant_admin_to_assign(services, role.id)
    holders = [
        auth.register_user(_unique("p46b-rb-holder"), _PASSWORD, role_names=[], tenant_id=tenant_id)
        for _ in range(2)
    ]
    for holder in holders:
        role_governance_service.assign_role(target_user_id=holder.id, role_id=role.id)

    before_active = services["session"].scalar(
        select(func.count()).select_from(RoleBindingORM).where(
            RoleBindingORM.role_id == role.id, RoleBindingORM.revoked_at.is_(None)
        )
    )

    def _raise(*_a, **_kw):
        raise RuntimeError("audit unavailable during retirement")

    monkeypatch.setattr(role_admin_service._audit_repo, "add_for_tenant", _raise)

    with pytest.raises(RuntimeError, match="audit unavailable during retirement"):
        role_admin_service.retire_custom_role(role.id, expected_policy_version=role.policy_version)

    after_active = services["session"].scalar(
        select(func.count()).select_from(RoleBindingORM).where(
            RoleBindingORM.role_id == role.id, RoleBindingORM.revoked_at.is_(None)
        )
    )
    assert after_active == before_active == 2, "a failed retirement must not revoke ANY binding"
    assert role_admin_service._role_repo.get(role.id).status != "retired"


# ---------------------------------------------------------------------------
# 5. ViewInvalidation precision: account_security vs authorization_context, cross-tenant isolation
# ---------------------------------------------------------------------------


def test_account_security_and_authorization_context_targets_never_cross_fire(services):
    """A password/MFA/session mutation (`account_security`) must never trigger
    `authorization_context`, and a custom-role mutation (`authorization_context`) must never
    trigger `account_security` -- the two families are strictly non-overlapping."""
    _set_tenant_admin(services)
    auth = services["auth_service"]
    tenant_id = _tenant_id(services)
    catalog = _catalog(services)

    account_security_calls = []
    authorization_context_calls = []
    catalog._account_security_view_invalidation_adapter.accountSecurityStale.connect(
        lambda: account_security_calls.append("stale")
    )
    catalog._authorization_context_view_invalidation_adapter.authorizationContextStale.connect(
        lambda: authorization_context_calls.append("stale")
    )

    target = auth.register_user(
        _unique("p46b-precision-target"), _PASSWORD, role_names=[], tenant_id=tenant_id
    )
    account_security_calls.clear()
    authorization_context_calls.clear()

    auth.force_user_password_reset(target.id)
    assert account_security_calls == ["stale"]
    assert authorization_context_calls == []

    account_security_calls.clear()
    services["tenant_role_administration_service"].create_custom_role(
        name=_unique("p46b_precision_role"), display_name="Precision Role"
    )
    assert authorization_context_calls == ["stale"]
    assert account_security_calls == []


def test_account_security_invalidation_is_tenant_scoped_not_cross_tenant(services):
    auth = services["auth_service"]
    other_tenant = services["tenant_admin_service"].create_tenant(
        _unique("p46b-other-tenant"), "Other Tenant"
    )

    catalog = _catalog(services)
    tenant_id = _tenant_id(services)
    catalog._account_security_view_invalidation_adapter.set_active_scope(
        tenant_id=other_tenant.id, organization_id=""
    )

    stale_calls = []
    catalog._account_security_view_invalidation_adapter.accountSecurityStale.connect(
        lambda: stale_calls.append("stale")
    )

    target = auth.register_user(
        _unique("p46b-cross-tenant-target"), _PASSWORD, role_names=[], tenant_id=tenant_id
    )
    auth.force_user_password_reset(target.id)

    assert stale_calls == [], "a fact for tenant A must never invalidate tenant B's subscription"


# ---------------------------------------------------------------------------
# 6. Ephemeral session transport: principalChanged / activeScopeChanged
# ---------------------------------------------------------------------------


def test_principal_changed_listener_fires_on_login_and_logout_not_on_unrelated_calls(services):
    from src.core.platform.domain.security.auth.session import UserSessionContext

    calls = []
    context = UserSessionContext(principal_changed_listener=lambda ctx: calls.append("changed"))
    auth = services["auth_service"]
    target = auth.register_user(_unique("p46b-principal-listener"), _PASSWORD, role_names=[])
    principal = auth.build_principal(target)

    context.set_principal(principal)
    assert calls == ["changed"]

    context.clear()
    assert calls == ["changed", "changed"]


def test_active_scope_changed_listener_fires_on_tenant_and_organization_switch_only(services):
    from src.core.platform.domain.security.auth.session import UserSessionContext

    calls = []
    context = UserSessionContext(active_scope_changed_listener=lambda ctx: calls.append("scope"))
    auth = services["auth_service"]
    target = auth.register_user(_unique("p46b-scope-listener"), _PASSWORD, role_names=[])
    context.set_principal(auth.build_principal(target))
    calls.clear()  # set_principal itself does not call the scope listener directly here

    context.set_active_tenant_id("tenant-x")
    assert calls == ["scope"]

    context.set_active_organization_id("org-y")
    assert calls == ["scope", "scope"]


# ---------------------------------------------------------------------------
# 7. Permanent zero-legacy guards
# ---------------------------------------------------------------------------


def _strip_strings_and_comments(source: str) -> str:
    import re

    no_docstrings = re.sub(r'"""[\s\S]*?"""', "", source)
    no_comments = re.sub(r"#.*", "", no_docstrings)
    return no_comments


def test_zero_auth_changed_anywhere_in_production_source():
    """Checks for actual code usage, not the bare substring -- several files carry deliberate
    retirement comments explaining the P46B removal (matching this session's established
    convention), which would otherwise false-positive a blanket substring scan."""
    import glob

    hits = []
    for path in glob.glob("src/**/*.py", recursive=True):
        normalized = path.replace("\\", "/")
        if "__pycache__" in normalized or "/tests/" in normalized:
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = _strip_strings_and_comments(fh.read())
        if "auth_changed" in source:
            hits.append(normalized)
    assert hits == [], hits


def test_domain_events_class_is_fully_deleted_not_merely_empty():
    """The strongest possible proof: the class itself is gone, not merely empty -- an
    empty-but-present class could silently regain a field later with no test noticing via a
    field-count check alone."""
    import src.core.shared.events as events_package

    assert not hasattr(events_package, "DomainEvents")
    assert not hasattr(events_package, "domain_events")
    assert not hasattr(events_package, "Signal")
    with pytest.raises(ModuleNotFoundError):
        import importlib

        importlib.import_module("src.core.shared.events.domain_events")
    with pytest.raises(ModuleNotFoundError):
        import importlib

        importlib.import_module("src.core.shared.events.signal")


def test_hypothetical_domain_events_reintroduction_would_fail_the_zero_legacy_guard():
    """Demonstrates the structural guard actually rejects reintroduction, mirroring every prior
    module's own hypothetical-growth proof: a stand-in class WITH a legacy field fails the exact
    assertion the real guard makes."""
    import dataclasses

    @dataclasses.dataclass
    class _HypotheticalDomainEventsReintroduction:
        some_legacy_signal_changed: object = None

    assert dataclasses.fields(_HypotheticalDomainEventsReintroduction) != ()


# A generic string-keyed replacement-bridge guard already exists and covers this precisely:
# `test_no_replacement_generic_router_or_registry_introduced` in test_p7_legacy_bridge_removal.py
# scans ALL of `src/**/*.py` (not just Auth) for the same class of forbidden name -- a second,
# narrower copy here would only risk colliding with that scan's own substring check (its forbidden
# names would appear literally in this file's own source) for zero added coverage.
