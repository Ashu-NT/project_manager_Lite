"""P5C-1 (Role Governance Transaction & Scope Convergence): `RoleGovernanceService` cut over from
the shared, process-lifetime `Session` and inline `commit()`/`rollback()` onto a canonical,
fresh-session `RoleGovernanceUnitOfWork` for all four mutation methods
(`assign_role`/`revoke_role_binding`/`create_delegation_policy`/`revoke_delegation_policy`).
Mirrors `test_organization_service_unit_of_work_cutover.py`/
`test_module_entitlement_transaction_convergence.py` (P4B/P5B's own equivalents).

This phase is transaction/scope convergence only -- no `RoleBindingAssigned`/`RoleBindingRevoked`
DomainEvent, no ViewInvalidation, no Qt migration, no `access_changed`/`auth_changed` removal.
`test_role_governance_p5c1_does_not_add_p5c2_event_vocabulary` enforces that phase boundary.
"""

from __future__ import annotations

import inspect
import re
from dataclasses import replace

import pytest

from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.infrastructure.persistence.repositories.security.auth.auth import (
    SqlAlchemyRoleBindingRepository,
)
from src.core.platform.infrastructure.persistence.role_governance_unit_of_work import (
    SqlAlchemyRoleGovernanceUnitOfWork,
)
from src.tests.ui_runtime_helpers import login_as

_COUNTER = {"n": 0}


def _unique_code(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _tenant_id(services) -> str:
    tenant_id = services["tenant_context_service"].get_active_tenant_id()
    assert tenant_id is not None
    return tenant_id


def _switch_session_to_actor(services, actor, *, tenant_id, organization_id=None, extra_permissions=()):
    """Mirrors the established pattern in `test_role_governance_foundation.py`: build a
    context-scoped principal for the delegated actor and add any permissions the delegation
    policy already covers redundantly, so the test does not depend on exactly which permissions
    happen to be pre-seeded on the actor's role."""
    auth = services["auth_service"]
    if organization_id is None:
        organization_id = services["tenant_context_service"].get_active_organization_id()
    principal = auth.build_principal_for_context(
        actor, tenant_id=tenant_id, organization_id=organization_id
    )
    services["user_session"].set_principal(
        replace(
            principal,
            session_id=None,
            permissions=frozenset({*principal.permissions, *extra_permissions}),
        )
    )


def _tenant_scoped_binding_setup(services, *, suffix: str, role_name: str = "viewer"):
    """Registers an actor (tenant_admin) + target under the still-active default (platform.admin)
    session, creates the tenant-wide delegation policy while that session can still author it,
    then switches the session onto the actor -- exactly the ordering `create_delegation_policy`
    (requires `platform.admin`) and `assign_role`/`revoke_role_binding` (reject a `platform.admin`
    actor) both demand."""
    auth = services["auth_service"]
    tenant_id = _tenant_id(services)
    actor = auth.register_user(
        f"p5c1-actor-{suffix}", "P5C1Actor123!", role_names=["tenant_admin"], tenant_id=tenant_id
    )
    target = auth.register_user(
        f"p5c1-target-{suffix}", "P5C1Target123!", role_names=[], tenant_id=tenant_id
    )
    actor_role = auth._role_repo.get_by_name("tenant_admin")
    target_role = auth._role_repo.get_by_name(role_name)
    services["role_governance_service"].create_delegation_policy(
        actor_role_id=actor_role.id,
        assignable_role_id=target_role.id,
        target_scope_type="tenant",
        tenant_id=tenant_id,
    )
    _switch_session_to_actor(
        services, actor, tenant_id=tenant_id, extra_permissions=("auth.role.assign",)
    )
    return target, target_role


# ---------------------------------------------------------------------------
# Fresh session per mutation
# ---------------------------------------------------------------------------


def test_fresh_session_per_assign_and_revoke_call(services, monkeypatch):
    target, target_role = _tenant_scoped_binding_setup(services, suffix="fresh-session")
    role_governance_service = services["role_governance_service"]
    seen_sessions = []
    original_create = type(role_governance_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen_sessions.append(uow._session)
        return uow

    monkeypatch.setattr(type(role_governance_service._uow_factory), "create", _spy_create)

    binding = role_governance_service.assign_role(target_user_id=target.id, role_id=target_role.id)
    role_governance_service.revoke_role_binding(binding.id)

    assert len(seen_sessions) == 2
    assert seen_sessions[0] is not seen_sessions[1]
    assert all(s is not services["session"] for s in seen_sessions)


def test_repository_and_audit_share_the_uow_session(services, monkeypatch):
    target, target_role = _tenant_scoped_binding_setup(services, suffix="shared-session")
    role_governance_service = services["role_governance_service"]
    seen = {}
    original_create = type(role_governance_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen["uow_session"] = uow._session
        seen["role_bindings_session"] = uow.role_bindings.session
        seen["audit_session"] = uow.audit.session
        return uow

    monkeypatch.setattr(type(role_governance_service._uow_factory), "create", _spy_create)

    role_governance_service.assign_role(target_user_id=target.id, role_id=target_role.id)

    assert seen["uow_session"] is seen["role_bindings_session"]
    assert seen["uow_session"] is seen["audit_session"]


def test_no_global_mutation_session_touch(services):
    target, target_role = _tenant_scoped_binding_setup(services, suffix="no-global-touch")
    legacy_session = services["session"]
    legacy_session.commit()

    services["role_governance_service"].assign_role(target_user_id=target.id, role_id=target_role.id)

    assert len(legacy_session.new) == 0
    assert len(legacy_session.dirty) == 0


# ---------------------------------------------------------------------------
# Audit atomicity / commit-failure rollback
# ---------------------------------------------------------------------------


def test_commit_failure_rolls_back_binding_and_audit_together(services, monkeypatch):
    target, target_role = _tenant_scoped_binding_setup(services, suffix="commit-fail")
    role_governance_service = services["role_governance_service"]
    captured_uow = {}
    original_create = type(role_governance_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        captured_uow["uow"] = uow
        return uow

    monkeypatch.setattr(type(role_governance_service._uow_factory), "create", _spy_create)

    def _fail_commit(self):
        raise RuntimeError("simulated role governance commit failure")

    monkeypatch.setattr(SqlAlchemyRoleGovernanceUnitOfWork, "commit", _fail_commit)

    seen_signals = []
    from src.core.shared.events.domain_events import domain_events

    domain_events.auth_changed.connect(seen_signals.append)
    try:
        with pytest.raises(RuntimeError, match="simulated role governance commit failure"):
            role_governance_service.assign_role(target_user_id=target.id, role_id=target_role.id)
    finally:
        domain_events.auth_changed.disconnect(seen_signals.append)

    uow = captured_uow["uow"]
    assert uow._committed is False
    assert uow._closed is True
    assert seen_signals == []  # no legacy notification for a rolled-back mutation
    persisted = SqlAlchemyRoleBindingRepository(services["session"]).get_active_for_assignment(
        principal_id=target.id,
        role_id=target_role.id,
        tenant_id=_tenant_id(services),
        actual_scope_type="tenant",
        actual_scope_id=None,
    )
    assert persisted is None


# ---------------------------------------------------------------------------
# Non-active organization / cross-tenant resource scopes
# ---------------------------------------------------------------------------


def test_storeroom_role_assignment_targets_a_non_active_organization(services):
    """The confirmed-and-fixed ambient-org bug (P5C prerequisite pass): granting a
    storeroom-scoped role must key off the STOREROOM's own organization, never the ambient
    active one."""
    tenant_context_service = services["tenant_context_service"]
    org_a1_id = tenant_context_service.get_active_organization_id()
    site_a1 = services["site_service"].create_site(
        site_code=_unique_code("P5C1-A1-SITE"), name="A1 Site", city="Berlin", currency_code="EUR"
    )
    storeroom_a1 = services["inventory_service"].create_storeroom(
        storeroom_code=_unique_code("P5C1-A1-ROOM"),
        name="A1 Storeroom",
        site_id=site_a1.id,
        status="ACTIVE",
        storeroom_type="MAIN",
    )
    assert storeroom_a1.organization_id == org_a1_id

    org_a2 = services["organization_service"].create_organization(
        organization_code=_unique_code("P5C1-A2"), display_name="P5C-1 Org A2"
    )
    tenant_context_service.set_active_organization(org_a2.id)
    assert tenant_context_service.get_active_organization_id() == org_a2.id

    auth = services["auth_service"]
    tenant_id = _tenant_id(services)
    actor = auth.register_user(
        _unique_code("p5c1-storeroom-actor"), "P5C1Actor123!", role_names=["tenant_admin"], tenant_id=tenant_id
    )
    target = auth.register_user(
        _unique_code("p5c1-storeroom-target"), "P5C1Target123!", role_names=[], tenant_id=tenant_id
    )
    actor_role = auth._role_repo.get_by_name("tenant_admin")
    storeroom_role = auth._role_repo.get_by_name("storeroom_viewer")
    services["role_governance_service"].create_delegation_policy(
        actor_role_id=actor_role.id,
        assignable_role_id=storeroom_role.id,
        target_scope_type="storeroom",
        tenant_id=tenant_id,
    )
    _switch_session_to_actor(
        services,
        actor,
        tenant_id=tenant_id,
        organization_id=org_a2.id,
        extra_permissions=("auth.role.assign",),
    )

    # Active organization is A2, but the storeroom being granted belongs to A1 -- must succeed
    # without switching back, per the confirmed-and-fixed ambient-scope bug.
    binding = services["role_governance_service"].assign_role(
        target_user_id=target.id,
        role_id=storeroom_role.id,
        actual_scope_id=storeroom_a1.id,
    )
    assert tenant_context_service.get_active_organization_id() == org_a2.id  # never switched
    assert binding.actual_scope_id == storeroom_a1.id


def test_project_role_assignment_in_a_non_active_organization_remains_a_confirmed_and_tracked_gap(
    services,
):
    """P5C-1 audit finding, NOT fixed in this phase: `ProjectRepository.get()`/`_base_stmt()`
    (`src/core/modules/project_management/infrastructure/persistence/repositories/projects/
    project.py`) is ITSELF ambiently scoped to the currently active organization
    (`ctx.organization_id` from `require_active_scope_ids`), so the "project" scope-exists
    resolver (`_project_belongs_to_tenant` in `project_registry.py`) inherits the same class of
    defect the storeroom resolver had -- just one layer deeper. Fixing it correctly requires a
    new tenant-scoped (non-active-org) read method on `ProjectRepository` (a Project-Management
    module change) or reaching into its ORM internals from Access/RBAC composition (a layering
    violation) -- both outside this phase's narrow "RoleGovernanceService transaction/scope
    convergence" boundary. This test characterizes the CURRENT (still-broken) behavior so a
    future fix is measured against a real, executable expectation rather than prose alone.

    ("site" is excluded here: no `scope_exists_resolver` is registered for "site" anywhere in
    composition today, so a "site"-scoped role assignment is unreachable regardless of this
    defect -- see `test_organization_and_site_role_assignment_are_not_yet_reachable` below.)
    """
    tenant_context_service = services["tenant_context_service"]
    org_a1_id = tenant_context_service.get_active_organization_id()
    project_a1 = services["project_service"].create_project("P5C-1 Non-Active Org Project")
    assert project_a1.organization_id == org_a1_id

    org_a2 = services["organization_service"].create_organization(
        organization_code=_unique_code("P5C1-PROJ-A2"), display_name="P5C-1 Project Org A2"
    )
    tenant_context_service.set_active_organization(org_a2.id)

    auth = services["auth_service"]
    tenant_id = _tenant_id(services)
    actor = auth.register_user(
        _unique_code("p5c1-project-actor"), "P5C1Actor123!", role_names=["tenant_admin"], tenant_id=tenant_id
    )
    target = auth.register_user(
        _unique_code("p5c1-project-target"), "P5C1Target123!", role_names=[], tenant_id=tenant_id
    )
    actor_role = auth._role_repo.get_by_name("tenant_admin")
    project_role = auth._role_repo.get_by_name("project_viewer")
    services["role_governance_service"].create_delegation_policy(
        actor_role_id=actor_role.id,
        assignable_role_id=project_role.id,
        target_scope_type="project",
        tenant_id=tenant_id,
    )
    _switch_session_to_actor(
        services,
        actor,
        tenant_id=tenant_id,
        organization_id=org_a2.id,
        extra_permissions=("auth.role.assign",),
    )

    # Confirmed tracked debt: this currently raises NotFoundError because the project belongs to
    # A1 while A2 is active -- the exact ambient-organization defect class, not yet fixed for
    # "project". Once a tenant-scoped (non-active-org) ProjectRepository read path exists, this
    # assertion should be updated to expect success instead.
    with pytest.raises(NotFoundError) as exc_info:
        services["role_governance_service"].assign_role(
            target_user_id=target.id,
            role_id=project_role.id,
            actual_scope_id=project_a1.id,
        )
    assert exc_info.value.code == "PROJECT_NOT_FOUND"
    assert tenant_context_service.get_active_organization_id() == org_a2.id


def test_organization_and_site_role_assignment_are_not_yet_reachable(services):
    """Neither "organization" nor "site" has a `register_scope_exists_resolver(...)` call
    anywhere in composition (confirmed by inspection of `platform_registry.py`/
    `project_registry.py`/`inventory_registry.py`) -- only "project" and "storeroom" do. So
    today, ANY role assignment at "organization" or "site" scope hits
    `AUTHORIZATION_SCOPE_RESOLVER_REQUIRED` before the P5C-1
    `organization_owner_resolvers["organization"]`/["site"] entries (registered in
    `platform_registry.py` for forward-readiness, per item 37 of the P5C-1 task) are ever
    consulted. This is the same currently-unreachable status "department" already had.
    Documented, not fixed -- registering the missing scope-exists resolvers is outside this
    phase's narrow transaction/scope-convergence boundary."""
    auth = services["auth_service"]
    tenant_id = _tenant_id(services)
    actor = auth.register_user(
        _unique_code("p5c1-unreachable-actor"), "P5C1Actor123!", role_names=["tenant_admin"], tenant_id=tenant_id
    )
    target = auth.register_user(
        _unique_code("p5c1-unreachable-target"), "P5C1Target123!", role_names=[], tenant_id=tenant_id
    )
    actor_role = auth._role_repo.get_by_name("tenant_admin")
    org_role = auth._role_repo.get_by_name("org_viewer")
    services["role_governance_service"].create_delegation_policy(
        actor_role_id=actor_role.id,
        assignable_role_id=org_role.id,
        target_scope_type="organization",
        tenant_id=tenant_id,
    )
    _switch_session_to_actor(
        services, actor, tenant_id=tenant_id, extra_permissions=("auth.role.assign",)
    )

    from src.core.platform.common.exceptions import BusinessRuleError

    active_org_id = services["tenant_context_service"].get_active_organization_id()
    with pytest.raises(BusinessRuleError) as exc_info:
        services["role_governance_service"].assign_role(
            target_user_id=target.id,
            role_id=org_role.id,
            actual_scope_id=active_org_id,
        )
    assert exc_info.value.code == "AUTHORIZATION_SCOPE_RESOLVER_REQUIRED"


def test_organization_owner_resolver_metadata_is_registered_and_correct_ahead_of_reachability(
    services,
):
    """The `organization_owner_resolvers` wired in `platform_registry.py` for "organization"
    (identity) and "site" (via the site's own `organization_id`) are event-readiness metadata
    for a future P5C-2 event, per item 37 of the P5C-1 task -- correct even though, per
    `test_organization_and_site_role_assignment_are_not_yet_reachable`, neither scope type is
    reachable through `assign_role` yet (no `scope_exists_resolver` registered for either)."""
    role_governance_service = services["role_governance_service"]
    organization_resolver = role_governance_service._organization_owner_resolvers.get("organization")
    site_resolver = role_governance_service._organization_owner_resolvers.get("site")
    assert organization_resolver is not None
    assert site_resolver is not None

    tenant_id = _tenant_id(services)
    org_id = services["tenant_context_service"].get_active_organization_id()
    assert organization_resolver(tenant_id, org_id) == org_id

    site = services["site_service"].create_site(
        site_code=_unique_code("P5C1-RESOLVER-SITE"), name="Resolver Site", city="Berlin", currency_code="EUR"
    )
    assert site_resolver(tenant_id, site.id) == org_id


def test_storeroom_role_assignment_rejects_a_foreign_tenant_storeroom(services):
    """A storeroom that belongs to a wholly different tenant must never be grantable from the
    current tenant's role governance -- the "storeroom" `scope_exists_resolver`
    (`_storeroom_exists` in `inventory_registry.py`) checks
    `organization_repo.get_for_tenant(storeroom.organization_id, tenant_id)`, which is `None`
    for a foreign-tenant organization."""
    from datetime import datetime, timezone

    from src.core.platform.infrastructure.persistence.orm.master_data.org.org import OrganizationORM
    from src.core.platform.infrastructure.persistence.orm.master_data.site.sites import SiteORM
    from src.core.platform.infrastructure.persistence.orm.tenant.tenancy.tenant import TenantORM
    from src.core.modules.inventory_procurement.infrastructure.persistence.orm.inventory import StoreroomORM

    now = datetime.now(timezone.utc)
    session = services["session"]
    auth = services["auth_service"]
    tenant_id = _tenant_id(services)
    actor = auth.register_user(
        _unique_code("p5c1-cross-tenant-actor"), "P5C1Actor123!", role_names=["tenant_admin"], tenant_id=tenant_id
    )
    target = auth.register_user(
        _unique_code("p5c1-cross-tenant-target"), "P5C1Target123!", role_names=[], tenant_id=tenant_id
    )
    actor_role = auth._role_repo.get_by_name("tenant_admin")
    storeroom_role = auth._role_repo.get_by_name("storeroom_viewer")
    services["role_governance_service"].create_delegation_policy(
        actor_role_id=actor_role.id,
        assignable_role_id=storeroom_role.id,
        target_scope_type="storeroom",
        tenant_id=tenant_id,
    )

    foreign_tenant_id = _unique_code("p5c1-foreign-tenant")
    session.add(
        TenantORM(
            id=foreign_tenant_id,
            tenant_code=_unique_code("P5C1FT"),
            display_name="Foreign Tenant",
            is_active=True,
            version=1,
        )
    )
    session.commit()
    foreign_org_id = _unique_code("p5c1-foreign-org")
    session.add(
        OrganizationORM(
            id=foreign_org_id,
            tenant_id=foreign_tenant_id,
            organization_code=_unique_code("P5C1FORG"),
            display_name="Foreign Org",
            is_active=True,
            version=1,
        )
    )
    session.commit()
    foreign_site_id = _unique_code("p5c1-foreign-site")
    session.add(
        SiteORM(
            id=foreign_site_id,
            tenant_id=foreign_tenant_id,
            organization_id=foreign_org_id,
            site_code=_unique_code("P5C1FSITE"),
            name="Foreign Site",
            is_active=True,
            created_at=now,
            updated_at=now,
            version=1,
        )
    )
    session.commit()
    foreign_storeroom_id = _unique_code("p5c1-foreign-storeroom")
    session.add(
        StoreroomORM(
            id=foreign_storeroom_id,
            tenant_id=foreign_tenant_id,
            organization_id=foreign_org_id,
            site_id=foreign_site_id,
            storeroom_code=_unique_code("P5C1FROOM"),
            name="Foreign Storeroom",
            status="ACTIVE",
            created_at=now,
            updated_at=now,
            version=1,
        )
    )
    session.commit()

    _switch_session_to_actor(
        services, actor, tenant_id=tenant_id, extra_permissions=("auth.role.assign",)
    )

    with pytest.raises(NotFoundError) as exc_info:
        services["role_governance_service"].assign_role(
            target_user_id=target.id,
            role_id=storeroom_role.id,
            actual_scope_id=foreign_storeroom_id,
        )
    assert exc_info.value.code == "STOREROOM_NOT_FOUND"


# ---------------------------------------------------------------------------
# Current-principal refresh: ordering + fail-closed failure characterization
# ---------------------------------------------------------------------------


def test_self_assignment_refreshes_current_principal_only_after_commit(services):
    """The real production path (`AuthService.assign_role`/`.revoke_role`, the legacy tenant-role
    facade over `RoleGovernanceService`) calls `refresh_current_session_if_user` AFTER the
    canonical UoW commits -- proven end to end: an admin assigning themselves a brand-new role
    must see it appear in their own session immediately, and disappear immediately on revoke.
    `RoleGovernanceService.assign_role`/`revoke_role_binding` themselves never call this refresh
    (confirmed by reading the source) -- it is deliberately the calling facade's responsibility,
    which this test exercises directly rather than assuming."""
    auth = services["auth_service"]
    tenant_id = _tenant_id(services)
    username = _unique_code("p5c1-self-actor")
    self_actor = auth.register_user(
        username, "P5C1SelfActor123!", role_names=["tenant_admin"], tenant_id=tenant_id
    )
    tenant_admin_role = auth._role_repo.get_by_name("tenant_admin")
    viewer_role = auth._role_repo.get_by_name("viewer")
    services["role_governance_service"].create_delegation_policy(
        actor_role_id=tenant_admin_role.id,
        assignable_role_id=viewer_role.id,
        target_scope_type="tenant",
        tenant_id=tenant_id,
    )

    login_as(services, username, "P5C1SelfActor123!")
    assert "viewer" not in services["user_session"].principal.role_names

    auth.assign_role(self_actor.id, "viewer")
    assert "viewer" in services["user_session"].principal.role_names

    auth.revoke_role(self_actor.id, "viewer")
    assert "viewer" not in services["user_session"].principal.role_names


def test_other_user_mutation_does_not_refresh_the_calling_actors_own_principal(services):
    target, target_role = _tenant_scoped_binding_setup(
        services, suffix="other-user-no-self-refresh"
    )
    calling_actor_principal_before = services["user_session"].principal

    services["role_governance_service"].assign_role(target_user_id=target.id, role_id=target_role.id)

    # `refresh_current_session_if_user` guards on `principal.user_id != user_id` -- a mutation
    # targeting a DIFFERENT user must never touch the calling actor's own session principal.
    assert services["user_session"].principal is calling_actor_principal_before


def test_current_principal_refresh_failure_after_commit_fails_closed(services, monkeypatch):
    """P5C-1 characterization (item 24): if rebuilding the principal raises AFTER the RoleBinding
    transaction has already committed, the established `refresh_current_session_if_user` helper
    (unchanged by this phase, still reached via the `AuthService.revoke_role` facade) clears the
    session entirely -- fail-closed -- rather than silently continuing with a stale principal. No
    broader auth redesign is required; this proves the existing mechanism survives the UoW
    migration unchanged."""
    auth = services["auth_service"]
    tenant_id = _tenant_id(services)
    username = _unique_code("p5c1-refresh-fail-actor")
    self_actor = auth.register_user(
        username, "P5C1RefreshFail123!", role_names=["tenant_admin"], tenant_id=tenant_id
    )
    tenant_admin_role = auth._role_repo.get_by_name("tenant_admin")
    viewer_role = auth._role_repo.get_by_name("viewer")
    services["role_governance_service"].create_delegation_policy(
        actor_role_id=tenant_admin_role.id,
        assignable_role_id=viewer_role.id,
        target_scope_type="tenant",
        tenant_id=tenant_id,
    )

    login_as(services, username, "P5C1RefreshFail123!")
    auth.assign_role(self_actor.id, "viewer")
    assert "viewer" in services["user_session"].principal.role_names

    def _fail_build_principal(*_args, **_kwargs):
        raise RuntimeError("simulated build_principal failure")

    monkeypatch.setattr(
        "src.core.platform.application.security.auth.session.session_service.build_principal",
        _fail_build_principal,
    )

    # Must NOT raise -- the fail-closed helper swallows the rebuild failure and clears instead.
    auth.revoke_role(self_actor.id, "viewer")

    assert services["user_session"].principal is None  # cleared, never left stale/elevated


# ---------------------------------------------------------------------------
# Facades remain non-transaction-owning
# ---------------------------------------------------------------------------


def test_access_facade_does_not_own_a_competing_transaction(services):
    site = services["site_service"].create_site(
        site_code=_unique_code("P5C1-FACADE-SITE"), name="Facade Site", city="Berlin", currency_code="EUR"
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code=_unique_code("P5C1-FACADE-ROOM"),
        name="Facade Storeroom",
        site_id=site.id,
        status="ACTIVE",
        storeroom_type="MAIN",
    )
    auth = services["auth_service"]
    tenant_id = _tenant_id(services)
    user = auth.register_user(
        _unique_code("p5c1-facade-user"), "P5C1Facade123!", role_names=["inventory_manager"], tenant_id=tenant_id
    )

    grant = services["access_service"].assign_scope_grant(
        scope_type="storeroom", scope_id=storeroom.id, user_id=user.id, scope_role="editor"
    )
    assert grant.scope_id == storeroom.id
    services["access_service"].remove_scope_grant(
        scope_type="storeroom", scope_id=storeroom.id, user_id=user.id
    )
    assert services["access_service"].list_scope_grants("storeroom", storeroom.id) == []


# ---------------------------------------------------------------------------
# Architecture guards
# ---------------------------------------------------------------------------


def _role_governance_service_source() -> str:
    module = __import__(
        "src.core.platform.application.security.authorization.roles.role_governance_service",
        fromlist=["role_governance_service"],
    )
    return inspect.getsource(module)


def test_role_governance_service_has_no_inline_commit_or_rollback_or_global_session():
    source = _role_governance_service_source()
    for forbidden in ("self._session.commit(", "self._session.rollback(", "session: Session", "self._session ="):
        assert forbidden not in source


def test_role_governance_p5c1_does_not_add_p5c2_event_vocabulary():
    """The service's docstrings legitimately MENTION the future `RoleBindingAssigned`/
    `RoleBindingRevoked` vocabulary (item 38's "future event field documentation"
    requirement) -- what must not exist yet is an actual emission of anything beyond the
    single retained legacy signal, or any ViewInvalidation/Qt dependency."""
    source = _role_governance_service_source()
    emitted_signals = set(re.findall(r"domain_events\.(\w+)\.emit\(", source))
    assert emitted_signals == {"auth_changed"}
    for forbidden in ("ViewInvalidation", "PySide6", "ui_qml"):
        assert forbidden not in source
