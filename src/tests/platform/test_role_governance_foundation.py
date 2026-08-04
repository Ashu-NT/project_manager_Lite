from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from src.core.platform.auth.domain import (
    ROLE_SCOPE_TENANT,
    Role,
    RoleBinding,
    RolePermissionBinding,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.domain.tenant.tenancy import Tenant
from src.infra.persistence.migrations.runner import run_migrations


_REPO_ROOT = Path(__file__).resolve().parents[3]
_MIGRATIONS_ROOT = (
    _REPO_ROOT / "src" / "infra" / "persistence" / "migrations"
)


def _alembic_config(database_url: str) -> Config:
    config = Config(str(_MIGRATIONS_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(_MIGRATIONS_ROOT))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _tenant_id(services) -> str:
    tenant_id = services["tenant_context_service"].get_active_tenant_id()
    assert tenant_id is not None
    return tenant_id


def _prepare_canonical_assignment(
    services,
    *,
    target_role_name: str = "viewer",
    create_policy: bool = True,
):
    auth = services["auth_service"]
    session = services["session"]
    tenant_id = _tenant_id(services)
    actor = auth.register_user(
        f"canonical-actor-{target_role_name}",
        "CanonicalActor123!",
        role_names=["tenant_admin"],
        tenant_id=tenant_id,
    )
    target = auth.register_user(
        f"canonical-target-{target_role_name}",
        "CanonicalTarget123!",
        role_names=[],
        tenant_id=tenant_id,
    )
    actor_role = auth._role_repo.get_by_name("tenant_admin")
    target_role = auth._role_repo.get_by_name(target_role_name)
    assert actor_role is not None
    assert target_role is not None
    if create_policy:
        services["role_governance_service"].create_delegation_policy(
            actor_role_id=actor_role.id,
            assignable_role_id=target_role.id,
            target_scope_type=ROLE_SCOPE_TENANT,
            tenant_id=tenant_id,
        )

    principal = auth.build_principal_for_context(
        actor,
        tenant_id=tenant_id,
        organization_id=(
            services["tenant_context_service"].get_active_organization_id()
        ),
    )
    services["user_session"].set_principal(
        replace(
            principal,
            session_id=None,
            permissions=frozenset(
                {*principal.permissions, "auth.role.assign"}
            ),
        )
    )
    return actor, target, target_role


def _prepare_organization_canonical_assignment(
    services,
    *,
    target_role_name: str,
    organization_id: str,
    create_policy: bool = True,
):
    auth = services["auth_service"]
    tenant_id = _tenant_id(services)
    actor = auth.register_user(
        f"org-canonical-actor-{target_role_name}",
        "CanonicalActor123!",
        role_names=["tenant_admin"],
        tenant_id=tenant_id,
    )
    target = auth.register_user(
        f"org-canonical-target-{target_role_name}",
        "CanonicalTarget123!",
        role_names=[],
        tenant_id=tenant_id,
    )
    actor_role = auth._role_repo.get_by_name("tenant_admin")
    target_role = auth._role_repo.get_by_name(target_role_name)
    assert actor_role is not None
    assert target_role is not None
    if create_policy:
        services["role_governance_service"].create_delegation_policy(
            actor_role_id=actor_role.id,
            assignable_role_id=target_role.id,
            target_scope_type="organization",
            tenant_id=tenant_id,
        )

    principal = auth.build_principal_for_context(
        actor,
        tenant_id=tenant_id,
        organization_id=organization_id,
    )
    services["user_session"].set_principal(
        replace(
            principal,
            session_id=None,
            permissions=frozenset(
                {*principal.permissions, "auth.role.assign"}
            ),
        )
    )
    return actor, target, target_role


def test_organization_role_assignment_is_scoped_and_audited(services) -> None:
    tenant_id = _tenant_id(services)
    organization_id = services["tenant_context_service"].get_active_organization_id()
    assert organization_id is not None
    _, target, target_role = _prepare_organization_canonical_assignment(
        services,
        target_role_name="org_viewer",
        organization_id=organization_id,
    )

    binding = services["role_governance_service"].assign_role(
        target_user_id=target.id,
        role_id=target_role.id,
        actual_scope_id=organization_id,
    )

    assert binding.tenant_id == tenant_id
    assert binding.actual_scope_type == "organization"
    assert binding.actual_scope_id == organization_id


def test_organization_role_assignment_rejects_cross_tenant_organization(
    services,
) -> None:
    organization_id = services["tenant_context_service"].get_active_organization_id()
    assert organization_id is not None
    _, target, target_role = _prepare_organization_canonical_assignment(
        services,
        target_role_name="org_viewer",
        organization_id=organization_id,
    )
    other_tenant = Tenant.create(
        tenant_code="ORG-ROLE-OTHER",
        display_name="Other Org Role Tenant",
    )
    services["role_governance_service"]._tenant_repo.add(other_tenant)
    services["session"].flush()
    other_organization = Organization.create(
        organization_code="ORG-ROLE-OTHER-ORG",
        display_name="Other Org Role Organization",
        tenant_id=other_tenant.id,
    )
    services["organization_service"]._organization_repo.add(other_organization)
    services["session"].flush()

    with pytest.raises(NotFoundError) as exc_info:
        services["role_governance_service"].assign_role(
            target_user_id=target.id,
            role_id=target_role.id,
            actual_scope_id=other_organization.id,
        )

    assert exc_info.value.code == "ORGANIZATION_NOT_FOUND"


def _prepare_project_canonical_assignment(
    services,
    *,
    target_role_name: str,
    project_id: str,
    create_policy: bool = True,
):
    auth = services["auth_service"]
    tenant_id = _tenant_id(services)
    actor = auth.register_user(
        f"project-canonical-actor-{target_role_name}",
        "CanonicalActor123!",
        role_names=["tenant_admin"],
        tenant_id=tenant_id,
    )
    target = auth.register_user(
        f"project-canonical-target-{target_role_name}",
        "CanonicalTarget123!",
        role_names=[],
        tenant_id=tenant_id,
    )
    actor_role = auth._role_repo.get_by_name("tenant_admin")
    target_role = auth._role_repo.get_by_name(target_role_name)
    assert actor_role is not None
    assert target_role is not None
    if create_policy:
        services["role_governance_service"].create_delegation_policy(
            actor_role_id=actor_role.id,
            assignable_role_id=target_role.id,
            target_scope_type="project",
            tenant_id=tenant_id,
        )

    principal = auth.build_principal_for_context(
        actor,
        tenant_id=tenant_id,
        organization_id=services["tenant_context_service"].get_active_organization_id(),
    )
    services["user_session"].set_principal(
        replace(
            principal,
            session_id=None,
            permissions=frozenset(
                {*principal.permissions, "auth.role.assign"}
            ),
        )
    )
    return actor, target, target_role


def test_project_role_assignment_is_scoped_and_audited(services) -> None:
    tenant_id = _tenant_id(services)
    project = services["project_service"].create_project("Governance Project A")
    _, target, target_role = _prepare_project_canonical_assignment(
        services,
        target_role_name="project_viewer",
        project_id=project.id,
    )

    binding = services["role_governance_service"].assign_role(
        target_user_id=target.id,
        role_id=target_role.id,
        actual_scope_id=project.id,
    )

    assert binding.tenant_id == tenant_id
    assert binding.actual_scope_type == "project"
    assert binding.actual_scope_id == project.id


def test_project_role_assignment_rejects_unresolvable_project(services) -> None:
    project = services["project_service"].create_project("Governance Project B")
    _, target, target_role = _prepare_project_canonical_assignment(
        services,
        target_role_name="project_viewer",
        project_id=project.id,
    )

    with pytest.raises(NotFoundError) as exc_info:
        services["role_governance_service"].assign_role(
            target_user_id=target.id,
            role_id=target_role.id,
            actual_scope_id="nonexistent-project-id",
        )

    assert exc_info.value.code == "PROJECT_NOT_FOUND"


def _prepare_site_canonical_assignment(
    services,
    *,
    target_role_name: str,
    site_id: str,
    create_policy: bool = True,
):
    auth = services["auth_service"]
    tenant_id = _tenant_id(services)
    actor = auth.register_user(
        f"site-canonical-actor-{target_role_name}",
        "CanonicalActor123!",
        role_names=["tenant_admin"],
        tenant_id=tenant_id,
    )
    target = auth.register_user(
        f"site-canonical-target-{target_role_name}",
        "CanonicalTarget123!",
        role_names=[],
        tenant_id=tenant_id,
    )
    actor_role = auth._role_repo.get_by_name("tenant_admin")
    target_role = auth._role_repo.get_by_name(target_role_name)
    assert actor_role is not None
    assert target_role is not None
    if create_policy:
        services["role_governance_service"].create_delegation_policy(
            actor_role_id=actor_role.id,
            assignable_role_id=target_role.id,
            target_scope_type="site",
            tenant_id=tenant_id,
        )

    principal = auth.build_principal_for_context(
        actor,
        tenant_id=tenant_id,
        organization_id=services["tenant_context_service"].get_active_organization_id(),
    )
    services["user_session"].set_principal(
        replace(
            principal,
            session_id=None,
            permissions=frozenset(
                {*principal.permissions, "auth.role.assign"}
            ),
        )
    )
    return actor, target, target_role


def test_site_role_assignment_is_scoped_and_audited(services) -> None:
    tenant_id = _tenant_id(services)
    site = services["site_service"].create_site(
        site_code="GOV-SITE-A",
        name="Governance Site A",
        city="Berlin",
        currency_code="EUR",
    )
    _, target, target_role = _prepare_site_canonical_assignment(
        services,
        target_role_name="site_viewer",
        site_id=site.id,
    )

    binding = services["role_governance_service"].assign_role(
        target_user_id=target.id,
        role_id=target_role.id,
        actual_scope_id=site.id,
    )

    assert binding.tenant_id == tenant_id
    assert binding.actual_scope_type == "site"
    assert binding.actual_scope_id == site.id


def test_site_role_assignment_rejects_unresolvable_site(services) -> None:
    site = services["site_service"].create_site(
        site_code="GOV-SITE-B",
        name="Governance Site B",
        city="Berlin",
        currency_code="EUR",
    )
    _, target, target_role = _prepare_site_canonical_assignment(
        services,
        target_role_name="site_viewer",
        site_id=site.id,
    )

    with pytest.raises(NotFoundError) as exc_info:
        services["role_governance_service"].assign_role(
            target_user_id=target.id,
            role_id=target_role.id,
            actual_scope_id="nonexistent-site-id",
        )

    assert exc_info.value.code == "SITE_NOT_FOUND"


def _create_storeroom(services, storeroom_code: str):
    site = services["site_service"].create_site(
        site_code=f"{storeroom_code}-SITE",
        name=f"{storeroom_code} Site",
        city="Berlin",
        currency_code="EUR",
    )
    return services["inventory_service"].create_storeroom(
        storeroom_code=storeroom_code,
        name=f"{storeroom_code} Storeroom",
        site_id=site.id,
        status="ACTIVE",
        storeroom_type="MAIN",
    )


def _prepare_storeroom_canonical_assignment(
    services,
    *,
    target_role_name: str,
    storeroom_id: str,
    create_policy: bool = True,
):
    auth = services["auth_service"]
    tenant_id = _tenant_id(services)
    actor = auth.register_user(
        f"storeroom-canonical-actor-{target_role_name}",
        "CanonicalActor123!",
        role_names=["tenant_admin"],
        tenant_id=tenant_id,
    )
    target = auth.register_user(
        f"storeroom-canonical-target-{target_role_name}",
        "CanonicalTarget123!",
        role_names=[],
        tenant_id=tenant_id,
    )
    actor_role = auth._role_repo.get_by_name("tenant_admin")
    target_role = auth._role_repo.get_by_name(target_role_name)
    assert actor_role is not None
    assert target_role is not None
    if create_policy:
        services["role_governance_service"].create_delegation_policy(
            actor_role_id=actor_role.id,
            assignable_role_id=target_role.id,
            target_scope_type="storeroom",
            tenant_id=tenant_id,
        )

    principal = auth.build_principal_for_context(
        actor,
        tenant_id=tenant_id,
        organization_id=services["tenant_context_service"].get_active_organization_id(),
    )
    services["user_session"].set_principal(
        replace(
            principal,
            session_id=None,
            permissions=frozenset(
                {*principal.permissions, "auth.role.assign"}
            ),
        )
    )
    return actor, target, target_role


def test_storeroom_role_assignment_is_scoped_and_audited(services) -> None:
    tenant_id = _tenant_id(services)
    storeroom = _create_storeroom(services, "GOV-STOREROOM-A")
    _, target, target_role = _prepare_storeroom_canonical_assignment(
        services,
        target_role_name="storeroom_viewer",
        storeroom_id=storeroom.id,
    )

    binding = services["role_governance_service"].assign_role(
        target_user_id=target.id,
        role_id=target_role.id,
        actual_scope_id=storeroom.id,
    )

    assert binding.tenant_id == tenant_id
    assert binding.actual_scope_type == "storeroom"
    assert binding.actual_scope_id == storeroom.id


def test_storeroom_role_assignment_rejects_unresolvable_storeroom(services) -> None:
    storeroom = _create_storeroom(services, "GOV-STOREROOM-B")
    _, target, target_role = _prepare_storeroom_canonical_assignment(
        services,
        target_role_name="storeroom_viewer",
        storeroom_id=storeroom.id,
    )

    with pytest.raises(NotFoundError) as exc_info:
        services["role_governance_service"].assign_role(
            target_user_id=target.id,
            role_id=target_role.id,
            actual_scope_id="nonexistent-storeroom-id",
        )

    assert exc_info.value.code == "STOREROOM_NOT_FOUND"


def _create_maintenance_location(services, location_code: str):
    site = services["site_service"].create_site(
        site_code=f"{location_code}-SITE",
        name=f"{location_code} Site",
        city="Berlin",
        currency_code="EUR",
    )
    return services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code=location_code,
        name=f"{location_code} Location",
        description="",
    )


def _prepare_maintenance_canonical_assignment(
    services,
    *,
    target_role_name: str,
    location_id: str,
    create_policy: bool = True,
):
    auth = services["auth_service"]
    tenant_id = _tenant_id(services)
    actor = auth.register_user(
        f"maintenance-canonical-actor-{target_role_name}",
        "CanonicalActor123!",
        role_names=["tenant_admin"],
        tenant_id=tenant_id,
    )
    target = auth.register_user(
        f"maintenance-canonical-target-{target_role_name}",
        "CanonicalTarget123!",
        role_names=[],
        tenant_id=tenant_id,
    )
    actor_role = auth._role_repo.get_by_name("tenant_admin")
    target_role = auth._role_repo.get_by_name(target_role_name)
    assert actor_role is not None
    assert target_role is not None
    if create_policy:
        services["role_governance_service"].create_delegation_policy(
            actor_role_id=actor_role.id,
            assignable_role_id=target_role.id,
            target_scope_type="maintenance",
            tenant_id=tenant_id,
        )

    principal = auth.build_principal_for_context(
        actor,
        tenant_id=tenant_id,
        organization_id=services["tenant_context_service"].get_active_organization_id(),
    )
    services["user_session"].set_principal(
        replace(
            principal,
            session_id=None,
            permissions=frozenset(
                {*principal.permissions, "auth.role.assign"}
            ),
        )
    )
    return actor, target, target_role


def test_maintenance_role_assignment_is_scoped_and_audited(services) -> None:
    tenant_id = _tenant_id(services)
    location = _create_maintenance_location(services, "GOV-MAINTENANCE-A")
    _, target, target_role = _prepare_maintenance_canonical_assignment(
        services,
        target_role_name="maintenance_viewer",
        location_id=location.id,
    )

    binding = services["role_governance_service"].assign_role(
        target_user_id=target.id,
        role_id=target_role.id,
        actual_scope_id=location.id,
    )

    assert binding.tenant_id == tenant_id
    assert binding.actual_scope_type == "maintenance"
    assert binding.actual_scope_id == location.id


def test_maintenance_role_assignment_rejects_unresolvable_location(services) -> None:
    location = _create_maintenance_location(services, "GOV-MAINTENANCE-B")
    _, target, target_role = _prepare_maintenance_canonical_assignment(
        services,
        target_role_name="maintenance_viewer",
        location_id=location.id,
    )

    with pytest.raises(NotFoundError) as exc_info:
        services["role_governance_service"].assign_role(
            target_user_id=target.id,
            role_id=target_role.id,
            actual_scope_id="nonexistent-maintenance-entity-id",
        )

    assert exc_info.value.code == "MAINTENANCE_NOT_FOUND"


def test_role_domain_enforces_system_and_tenant_ownership() -> None:
    with pytest.raises(ValidationError) as system_error:
        Role.create(
            name="invalid_system",
            is_system=True,
            tenant_id="tenant-a",
        )
    assert system_error.value.code == "AUTH_SYSTEM_ROLE_TENANT_INVALID"

    with pytest.raises(ValidationError) as custom_error:
        Role.create(
            name="invalid_custom",
            is_system=False,
        )
    assert custom_error.value.code == "AUTH_CUSTOM_ROLE_TENANT_REQUIRED"


def test_role_repository_uses_system_and_per_tenant_namespaces(
    session,
) -> None:
    from src.infra.composition.repositories import build_repository_bundle

    repositories = build_repository_bundle(session)
    tenant_a = Tenant.create(
        tenant_code="ROLE-A",
        display_name="Role Tenant A",
    )
    tenant_b = Tenant.create(
        tenant_code="ROLE-B",
        display_name="Role Tenant B",
    )
    system_role = Role.create(name="planner")
    tenant_a_role = Role.create(
        name="planner",
        is_system=False,
        tenant_id=tenant_a.id,
    )
    tenant_b_role = Role.create(
        name="planner",
        is_system=False,
        tenant_id=tenant_b.id,
    )
    repositories.tenant_repo.add(tenant_a)
    repositories.tenant_repo.add(tenant_b)
    session.flush()
    repositories.role_repo.add(system_role)
    repositories.role_repo.add(tenant_a_role)
    repositories.role_repo.add(tenant_b_role)
    session.commit()

    assert repositories.role_repo.get_by_name("planner") == system_role
    assert (
        repositories.role_repo.get_for_tenant_by_name(
            tenant_a.id,
            "planner",
        )
        == tenant_a_role
    )
    assert (
        repositories.role_repo.get_for_tenant_by_name(
            tenant_b.id,
            "planner",
        )
        == tenant_b_role
    )

    repositories.role_repo.add(
        Role.create(
            name="planner",
            is_system=False,
            tenant_id=tenant_a.id,
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_canonical_assignment_requires_explicit_delegation(services) -> None:
    _, target, target_role = _prepare_canonical_assignment(
        services,
        target_role_name="team_member",
        create_policy=False,
    )
    events = []
    services["user_session"].set_security_denial_listener(events.append)

    with pytest.raises(BusinessRuleError) as exc_info:
        services["role_governance_service"].assign_role(
            target_user_id=target.id,
            role_id=target_role.id,
        )

    assert exc_info.value.code == "ROLE_DELEGATION_DENIED"
    assert len(events) == 1
    assert events[0].operation == "authorization.delegation.denied"
    assert events[0].reason_code == "ROLE_DELEGATION_DENIED"
    assert events[0].target_scope_type == ROLE_SCOPE_TENANT


def test_canonical_assignment_is_tenant_scoped_and_audited(services) -> None:
    _, target, target_role = _prepare_canonical_assignment(services)

    binding = services["role_governance_service"].assign_role(
        target_user_id=target.id,
        role_id=target_role.id,
    )

    assert binding.tenant_id == _tenant_id(services)
    assert binding.actual_scope_type == ROLE_SCOPE_TENANT
    assert (
        services["role_governance_service"]._role_binding_repo.get(
            binding.id
        )
        == binding
    )


def test_expired_binding_is_revoked_before_reassignment(services) -> None:
    _, target, target_role = _prepare_canonical_assignment(services)
    now = datetime.now(timezone.utc)
    expired = RoleBinding(
        id="expired-canonical-binding",
        principal_type="user",
        principal_id=target.id,
        role_id=target_role.id,
        tenant_id=_tenant_id(services),
        actual_scope_type=ROLE_SCOPE_TENANT,
        actual_scope_id=None,
        assigned_by=None,
        assigned_at=now - timedelta(days=2),
        expires_at=now - timedelta(days=1),
        revoked_at=None,
        version=1,
    )
    services["role_governance_service"]._role_binding_repo.add(expired)
    services["session"].commit()

    replacement = services["role_governance_service"].assign_role(
        target_user_id=target.id,
        role_id=target_role.id,
    )

    retired = services["role_governance_service"]._role_binding_repo.get(
        expired.id
    )
    assert retired is not None
    assert retired.revoked_at is not None
    assert retired.version == 2
    assert replacement.id != expired.id


def test_permission_drift_invalidates_delegation_snapshot(services) -> None:
    auth = services["auth_service"]
    _, target, target_role = _prepare_canonical_assignment(services)
    permission = auth._permission_repo.get_by_code("settings.manage")
    assert permission is not None
    auth._role_permission_repo.add(
        RolePermissionBinding.create(
            role_id=target_role.id,
            permission_id=permission.id,
        )
    )
    services["session"].commit()

    with pytest.raises(BusinessRuleError) as exc_info:
        services["role_governance_service"].assign_role(
            target_user_id=target.id,
            role_id=target_role.id,
        )

    assert exc_info.value.code == "ROLE_DELEGATION_POLICY_STALE"


def test_tenant_owned_role_cannot_cross_tenant_namespace(services) -> None:
    _, target, _ = _prepare_canonical_assignment(services)
    other_tenant = Tenant.create(
        tenant_code="ROLE-OTHER",
        display_name="Other Role Tenant",
    )
    services["role_governance_service"]._tenant_repo.add(other_tenant)
    services["session"].flush()
    other_role = Role.create(
        name="other_tenant_planner",
        is_system=False,
        tenant_id=other_tenant.id,
    )
    services["role_governance_service"]._role_repo.add(other_role)
    services["session"].commit()

    with pytest.raises(BusinessRuleError) as exc_info:
        services["role_governance_service"].assign_role(
            target_user_id=target.id,
            role_id=other_role.id,
        )

    assert exc_info.value.code == "ROLE_CROSS_TENANT_DENIED"


def test_legacy_role_catalog_does_not_leak_or_offer_custom_roles(
    services,
) -> None:
    _prepare_canonical_assignment(services)
    current_tenant_id = _tenant_id(services)
    other_tenant = Tenant.create(
        tenant_code="ROLE-CATALOG-OTHER",
        display_name="Other Catalog Tenant",
    )
    role_repo = services["role_governance_service"]._role_repo
    services["role_governance_service"]._tenant_repo.add(other_tenant)
    services["session"].flush()
    current_role = Role.create(
        name="current_custom_role",
        is_system=False,
        tenant_id=current_tenant_id,
    )
    other_role = Role.create(
        name="other_custom_role",
        is_system=False,
        tenant_id=other_tenant.id,
    )
    role_repo.add(current_role)
    role_repo.add(other_role)
    services["session"].commit()

    listed_ids = {
        role.id for role in services["auth_service"].list_roles()
    }
    legacy_assignable_ids = {
        role.id
        for role in services[
            "auth_service"
        ].list_customer_assignable_roles()
    }

    assert current_role.id in listed_ids
    assert other_role.id not in listed_ids
    assert current_role.id not in legacy_assignable_ids
    assert other_role.id not in legacy_assignable_ids


def test_canonical_assignment_enforces_separation_of_duties(
    services,
) -> None:
    _, target, approver_role = _prepare_canonical_assignment(
        services,
        target_role_name="approver",
    )
    planner_role = services["auth_service"]._role_repo.get_by_name("planner")
    assert planner_role is not None
    services["role_governance_service"]._role_binding_repo.add(
        RoleBinding.create(
            principal_id=target.id,
            role_id=planner_role.id,
            tenant_id=_tenant_id(services),
            actual_scope_type=ROLE_SCOPE_TENANT,
        )
    )
    services["session"].commit()
    events = []
    services["user_session"].set_security_denial_listener(events.append)

    with pytest.raises(ValidationError) as exc_info:
        services["role_governance_service"].assign_role(
            target_user_id=target.id,
            role_id=approver_role.id,
        )

    assert exc_info.value.code == "ROLE_CONFLICT"
    assert len(events) == 1
    assert events[0].operation == "authorization.sod.denied"
    assert events[0].reason_code == "ROLE_CONFLICT"
    assert events[0].target_scope_id == target.id


def test_canonical_binding_revocation_uses_same_delegation_guard(
    services,
) -> None:
    _, target, target_role = _prepare_canonical_assignment(services)
    binding = services["role_governance_service"].assign_role(
        target_user_id=target.id,
        role_id=target_role.id,
    )

    revoked = services["role_governance_service"].revoke_role_binding(
        binding.id
    )

    assert revoked.revoked_at is not None
    assert revoked.version == binding.version + 1
    persisted = services[
        "role_governance_service"
    ]._role_binding_repo.get(binding.id)
    assert persisted is not None
    assert persisted.revoked_at is not None


def test_canonical_assignment_rolls_back_when_audit_persistence_fails(
    services,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, target, target_role = _prepare_canonical_assignment(services)

    def _fail_audit(*_args, **_kwargs) -> None:
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(
        services["role_governance_service"]._audit_repo,
        "add_for_tenant",
        _fail_audit,
    )

    with pytest.raises(RuntimeError, match="audit unavailable"):
        services["role_governance_service"].assign_role(
            target_user_id=target.id,
            role_id=target_role.id,
        )

    assert (
        services[
            "role_governance_service"
        ]._role_binding_repo.get_active_for_assignment(
            principal_id=target.id,
            role_id=target_role.id,
            tenant_id=_tenant_id(services),
            actual_scope_type=ROLE_SCOPE_TENANT,
            actual_scope_id=None,
        )
        is None
    )


def test_platform_operator_cannot_use_customer_assignment_path(
    services,
) -> None:
    auth = services["auth_service"]
    target = auth.register_user(
        "canonical-platform-denied-target",
        "CanonicalTarget123!",
        role_names=["viewer"],
        tenant_id=_tenant_id(services),
    )
    role = auth._role_repo.get_by_name("viewer")
    assert role is not None
    services[
        "role_governance_service"
    ]._allow_platform_customer_context = False
    principal = services["user_session"].principal
    services["user_session"].set_principal(
        replace(
            principal,
            session_id=None,
            permissions=frozenset(
                {*principal.permissions, "auth.role.assign"}
            ),
        )
    )

    with pytest.raises(BusinessRuleError) as exc_info:
        services["role_governance_service"].assign_role(
            target_user_id=target.id,
            role_id=role.id,
        )

    assert exc_info.value.code == "PLATFORM_CUSTOMER_OPERATION_DENIED"


def test_role_governance_migration_builds_namespace_and_delegation_schema(
    tmp_path,
) -> None:
    database_path = tmp_path / "role-governance.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    run_migrations(database_url)

    engine = create_engine(database_url, future=True)
    try:
        with engine.connect() as connection:
            inspector = inspect(connection)
            role_indexes = {
                index["name"]
                for index in inspector.get_indexes("roles")
            }
            role_checks = {
                constraint["name"]
                for constraint in inspector.get_check_constraints("roles")
            }
            delegation_columns = {
                column["name"]
                for column in inspector.get_columns(
                    "role_delegation_policies"
                )
            }
            delegation_indexes = {
                index["name"]
                for index in inspector.get_indexes(
                    "role_delegation_policies"
                )
            }
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
    finally:
        engine.dispose()

    assert revision == ScriptDirectory.from_config(
        _alembic_config(database_url)
    ).get_current_head()
    assert {
        "ux_roles_system_name",
        "ux_roles_tenant_name",
    } <= role_indexes
    assert {
        "ck_roles_ownership",
        "ck_roles_custom_scope",
    } <= role_checks
    assert {
        "tenant_id",
        "actor_role_id",
        "assignable_role_id",
        "target_scope_type",
        "assignable_role_policy_version",
        "assignable_permission_set_hash",
        "created_by",
        "created_at",
        "revoked_at",
    } <= delegation_columns
    assert {
        "ux_role_delegation_active_system",
        "ux_role_delegation_active_tenant",
    } <= delegation_indexes


def test_role_governance_migration_round_trips_before_custom_role_cutover(
    tmp_path,
) -> None:
    database_path = tmp_path / "role-governance-round-trip.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    config = _alembic_config(database_url)
    command.upgrade(config, "head")
    command.downgrade(config, "7a2b3c4d5e6f")

    engine = create_engine(database_url, future=True)
    try:
        with engine.connect() as connection:
            inspector = inspect(connection)
            role_indexes = {
                index["name"]
                for index in inspector.get_indexes("roles")
            }
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            assert not inspector.has_table("role_delegation_policies")
    finally:
        engine.dispose()

    assert revision == "7a2b3c4d5e6f"
    assert "idx_roles_name" in role_indexes
    command.upgrade(config, "head")
