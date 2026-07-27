from __future__ import annotations

from src.core.platform.auth.domain import UserAccount
from src.core.platform.auth.passwords import hash_password
from src.core.platform.auth.policy import DEFAULT_ROLE_PERMISSIONS
from src.core.platform.tenancy import Tenant, TenancyMode
from src.infra.composition.platform_registry import build_platform_service_bundle
from src.infra.composition.repositories import build_repository_bundle
from src.infra.platform.security_config import (
    AuthorizationMigrationMode,
    DeploymentEnvironment,
    RuntimeSecurityConfiguration,
)


def _security_configuration(mode: TenancyMode) -> RuntimeSecurityConfiguration:
    return RuntimeSecurityConfiguration(
        deployment_environment=DeploymentEnvironment.TEST,
        tenancy_mode=mode,
        authorization_migration_mode=(
            AuthorizationMigrationMode.LEGACY_AUTHORITATIVE
        ),
    )


def test_saas_startup_does_not_create_customer_context_or_legacy_admin(session) -> None:
    repositories = build_repository_bundle(session)

    bundle = build_platform_service_bundle(
        session,
        repositories,
        runtime_security_configuration=_security_configuration(TenancyMode.SAAS),
    )

    assert repositories.user_repo.list_all() == []
    assert repositories.tenant_repo.list_all() == []
    assert repositories.organization_repo.list_all() == []
    assert bundle.user_session.active_tenant_id() is None
    assert bundle.user_session.active_organization_id() is None
    assert {
        role.name for role in repositories.role_repo.list_all()
    } == set(DEFAULT_ROLE_PERMISSIONS)


def test_saas_startup_does_not_promote_or_backfill_existing_user(session) -> None:
    repositories = build_repository_bundle(session)
    ordinary_admin_name_user = UserAccount.create(
        username="admin",
        password_hash=hash_password("OrdinaryUser123!"),
        display_name="Ordinary User",
    )
    existing_tenant = Tenant.create(
        tenant_code="EXISTING",
        display_name="Existing Tenant",
    )
    repositories.user_repo.add(ordinary_admin_name_user)
    repositories.tenant_repo.add(existing_tenant)
    session.commit()

    bundle = build_platform_service_bundle(
        session,
        repositories,
        runtime_security_configuration=_security_configuration(TenancyMode.SAAS),
    )

    admin_role = repositories.role_repo.get_by_name("admin")
    assert admin_role is not None
    assert not repositories.user_role_repo.exists(
        ordinary_admin_name_user.id,
        admin_role.id,
    )
    assert not repositories.user_tenant_repo.is_active_member(
        ordinary_admin_name_user.id,
        existing_tenant.id,
    )
    assert repositories.organization_repo.list_for_tenant(existing_tenant.id) == []
    assert bundle.user_session.active_tenant_id() is None
    assert bundle.user_session.active_organization_id() is None


def test_local_single_tenant_startup_retains_explicit_desktop_defaults(session) -> None:
    repositories = build_repository_bundle(session)

    bundle = build_platform_service_bundle(
        session,
        repositories,
        runtime_security_configuration=_security_configuration(
            TenancyMode.LOCAL_SINGLE_TENANT
        ),
    )

    admin = repositories.user_repo.get_by_username("admin")
    tenant = repositories.tenant_repo.get_default()
    assert admin is not None
    assert tenant is not None
    assert repositories.user_tenant_repo.is_active_member(admin.id, tenant.id)
    assert repositories.organization_repo.list_for_tenant(tenant.id)
    assert bundle.user_session.active_tenant_id() == tenant.id
    assert bundle.user_session.active_organization_id() is not None
