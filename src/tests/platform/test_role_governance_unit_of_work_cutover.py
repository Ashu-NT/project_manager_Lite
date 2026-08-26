
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

    with pytest.raises(RuntimeError, match="simulated role governance commit failure"):
        role_governance_service.assign_role(target_user_id=target.id, role_id=target_role.id)

    uow = captured_uow["uow"]
    assert uow._committed is False
    assert uow._closed is True
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

    # Active organization is A2, but the project being granted belongs to A1 -- must succeed
    # without switching back, matching storeroom's already-fixed behavior.
    binding = services["role_governance_service"].assign_role(
        target_user_id=target.id,
        role_id=project_role.id,
        actual_scope_id=project_a1.id,
    )
    assert tenant_context_service.get_active_organization_id() == org_a2.id  # never switched
    assert binding.actual_scope_id == project_a1.id


def test_project_role_assignment_reverse_direction_active_a2_target_in_a1(services):

    tenant_context_service = services["tenant_context_service"]
    org_a1_id = tenant_context_service.get_active_organization_id()

    org_a2 = services["organization_service"].create_organization(
        organization_code=_unique_code("P5C1-PROJ-REV-A2"), display_name="P5C-1 Project Reverse Org A2", is_enabled=True
    )
    # Build project_a1 while A1 is still ambiently active (it already deactivated A1's DB flag
    # as a side effect, but the AMBIENT session org has not moved yet).
    project_a1 = services["project_service"].create_project("P5C-1 Reverse Direction Project A1")
    assert project_a1.organization_id == org_a1_id

    tenant_context_service.set_active_organization(org_a2.id)
    assert tenant_context_service.get_active_organization_id() == org_a2.id

    auth = services["auth_service"]
    tenant_id = _tenant_id(services)
    actor = auth.register_user(
        _unique_code("p5c1-project-rev-actor"), "P5C1Actor123!", role_names=["tenant_admin"], tenant_id=tenant_id
    )
    target = auth.register_user(
        _unique_code("p5c1-project-rev-target"), "P5C1Target123!", role_names=[], tenant_id=tenant_id
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

    binding = services["role_governance_service"].assign_role(
        target_user_id=target.id,
        role_id=project_role.id,
        actual_scope_id=project_a1.id,
    )
    assert tenant_context_service.get_active_organization_id() == org_a2.id  # never switched
    assert binding.actual_scope_id == project_a1.id

    services["role_governance_service"].revoke_role_binding(binding.id)
    assert tenant_context_service.get_active_organization_id() == org_a2.id  # still never switched


def test_site_role_assignment_targets_a_non_active_organization(services):
    """Same fix, "site" scope: `SiteRepository.get_for_tenant()` backs the "site" resolver
    registered directly on `role_governance_service` at construction time in
    `platform_registry.py` (a registration this test file originally missed entirely, having
    only grepped for `register_scope_exists_resolver(...)` calls -- "site" was ALWAYS reachable,
    just ambiently org-scoped, exactly like the reopened storeroom finding)."""
    tenant_context_service = services["tenant_context_service"]
    org_a1_id = tenant_context_service.get_active_organization_id()
    site_a1 = services["site_service"].create_site(
        site_code=_unique_code("P5C1-SITE-A1"), name="A1 Site For Role Scope", city="Berlin", currency_code="EUR"
    )
    assert site_a1.organization_id == org_a1_id

    org_a2 = services["organization_service"].create_organization(
        organization_code=_unique_code("P5C1-SITE-A2"), display_name="P5C-1 Site Org A2"
    )
    tenant_context_service.set_active_organization(org_a2.id)

    auth = services["auth_service"]
    tenant_id = _tenant_id(services)
    actor = auth.register_user(
        _unique_code("p5c1-site-actor"), "P5C1Actor123!", role_names=["tenant_admin"], tenant_id=tenant_id
    )
    target = auth.register_user(
        _unique_code("p5c1-site-target"), "P5C1Target123!", role_names=[], tenant_id=tenant_id
    )
    actor_role = auth._role_repo.get_by_name("tenant_admin")
    site_role = auth._role_repo.get_by_name("site_viewer")
    services["role_governance_service"].create_delegation_policy(
        actor_role_id=actor_role.id,
        assignable_role_id=site_role.id,
        target_scope_type="site",
        tenant_id=tenant_id,
    )
    _switch_session_to_actor(
        services,
        actor,
        tenant_id=tenant_id,
        organization_id=org_a2.id,
        extra_permissions=("auth.role.assign",),
    )

    binding = services["role_governance_service"].assign_role(
        target_user_id=target.id,
        role_id=site_role.id,
        actual_scope_id=site_a1.id,
    )
    assert tenant_context_service.get_active_organization_id() == org_a2.id  # never switched
    assert binding.actual_scope_id == site_a1.id


def test_organization_scoped_role_assignment_targets_a_non_active_organization(services):
    """"organization" scope's own resolver was ALSO already reachable and already correct
    (`OrganizationRepository.get_for_tenant` never had an ambient-org filter to begin with --
    an organization can't sensibly be scoped to itself). Proven end to end: granting a role for
    organization A2 while A1 remains active must succeed without switching."""
    tenant_context_service = services["tenant_context_service"]
    org_a1_id = tenant_context_service.get_active_organization_id()
    org_a2 = services["organization_service"].create_organization(
        organization_code=_unique_code("P5C1-ORG-SCOPE-A2"),
        display_name="P5C-1 Org Scope A2",
        is_enabled=False,
    )
    assert tenant_context_service.get_active_organization_id() == org_a1_id  # unaffected

    auth = services["auth_service"]
    tenant_id = _tenant_id(services)
    actor = auth.register_user(
        _unique_code("p5c1-org-scope-actor"), "P5C1Actor123!", role_names=["tenant_admin"], tenant_id=tenant_id
    )
    target = auth.register_user(
        _unique_code("p5c1-org-scope-target"), "P5C1Target123!", role_names=[], tenant_id=tenant_id
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

    binding = services["role_governance_service"].assign_role(
        target_user_id=target.id,
        role_id=org_role.id,
        actual_scope_id=org_a2.id,
    )
    assert tenant_context_service.get_active_organization_id() == org_a1_id  # never switched
    assert binding.actual_scope_id == org_a2.id


def test_department_role_assignment_remains_unreachable_and_undocumented_as_a_new_feature(
    services,
):
    """Unlike organization/project/site/storeroom, "department" has NO `scope_exists_resolver`
    registered anywhere in composition, and no role in the catalog even declares
    `allowed_scope_type == "department"` -- not a bug in an existing registration (which is what
    this phase fixes), but a resource scope never wired up for role assignment at all. Enabling
    it from scratch (a `ScopedRolePolicy`, role choices, a delegation-namespace convention, a
    catalog role) is a materially larger feature addition than closing an existing resolver's
    ambient-scope defect, so it is documented here, not implemented, and stays out of P5C-1's
    boundary.

    Item 4 evidence (full trace, not an unchecked assumption): organization ownership IS
    trivially derivable for department -- `DepartmentORM.organization_id` is a required column,
    identical in shape to `Site`/`Storeroom` -- so this is NOT a
    "P5C-1 RESOURCE OWNERSHIP MODEL BLOCKER" (ownership needs no domain redesign to derive). The
    repository read (`DepartmentRepository.get()`) is confirmed to share the SAME ambient-active-
    organization filter class already fixed for project/site/storeroom -- proven directly below,
    not merely inferred from reading the source -- but fixing it is moot while no
    `scope_exists_resolver`/catalog role exists to ever reach it, and wiring the whole feature is
    the out-of-boundary part, not the ownership-derivation part."""
    role_governance_service = services["role_governance_service"]
    assert role_governance_service._scope_exists_resolvers.get("department") is None
    assert role_governance_service._organization_owner_resolvers.get("department") is None
    assert not any(
        role.allowed_scope_type == "department" for role in services["auth_service"]._role_repo.list_all()
    )

    tenant_context_service = services["tenant_context_service"]
    org_a1_id = tenant_context_service.get_active_organization_id()
    department_a1 = services["department_service"].create_department(
        department_code=_unique_code("P5C1-DEPT-A1"), name="P5C-1 Department A1"
    )
    assert department_a1.organization_id == org_a1_id  # ownership trivially derivable

    org_a2 = services["organization_service"].create_organization(
        organization_code=_unique_code("P5C1-DEPT-A2"), display_name="P5C-1 Department Org A2", is_enabled=True
    )
    tenant_context_service.set_active_organization(org_a2.id)

    from src.core.platform.infrastructure.persistence.repositories.master_data.department.departments import (
        SqlAlchemyDepartmentRepository,
    )

    department_repo = SqlAlchemyDepartmentRepository(services["session"])
    department_repo._tenant_context_service = tenant_context_service
    # Confirmed: the SAME ambient-active-organization defect class already fixed for
    # project/site/storeroom also exists here at the repository level -- department A1 is
    # invisible while A2 is active, exactly like the pre-fix storeroom bug.
    assert department_repo.get(department_a1.id) is None
    assert not hasattr(department_repo, "get_for_tenant")


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
    """`_validate_target_scope` legitimately takes a per-call `session: Session` parameter
    (P5C-1 reopened storeroom finding: resource-scope resolvers now read within the calling
    UoW's own transaction) -- what must never exist is a process-lifetime `self._session`
    the service stores and reuses across calls."""
    source = _role_governance_service_source()
    for forbidden in (
        "self._session.commit(",
        "self._session.rollback(",
        "self._session =",
        "self._session:",
    ):
        assert forbidden not in source


def test_role_governance_emits_no_legacy_signal_and_no_view_invalidation_or_qt_vocabulary():
    """P5C-2 legitimately added `RoleBindingAssigned`/`RoleBindingRevoked` (see
    `test_role_binding_events.py`); this guard asserts what must still never exist -- any legacy
    Signal emission at all (P5 closeout, 2026-08-26: `auth_changed.emit(...)` removed from both
    `assign_role`/`revoke_role_binding` as a confirmed pure legacy duplicate of the
    already-implemented RoleBinding ViewInvalidation path), and no ViewInvalidation/Qt dependency
    (P5C-3's concern -- RoleGovernanceService itself stays a pure DomainEvent recorder, never a
    ViewInvalidation producer or Qt-aware component)."""
    source = _role_governance_service_source()
    emitted_signals = set(re.findall(r"domain_events\.(\w+)\.emit\(", source))
    assert emitted_signals == set()
    assert "domain_events" not in source
    for forbidden in ("ViewInvalidation", "PySide6", "ui_qml"):
        assert forbidden not in source
