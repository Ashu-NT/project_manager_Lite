from __future__ import annotations

import pytest

from src.core.platform.auth.domain.session import UserSessionContext
from src.core.platform.tenancy.context_policy import (
    LocalSingleTenantContextPolicy,
    SaaSTenantContextPolicy,
    TenancyMode,
)
from src.core.platform.tenancy.domain.tenant import Tenant
from src.core.platform.tenancy.tenant_context import TenantContextService
from src.infra.platform.security_config import (
    AuthorizationMigrationMode,
    DeploymentEnvironment,
    RuntimeSecurityConfigurationError,
    load_runtime_security_configuration,
)


class _TenantRepository:
    def __init__(self, tenant: Tenant) -> None:
        self.tenant = tenant

    def get(self, tenant_id: str) -> Tenant | None:
        return self.tenant if tenant_id == self.tenant.id else None

    def get_default(self) -> Tenant:
        return self.tenant


class _OrganizationRepository:
    def get(self, organization_id: str):
        return None


def test_development_defaults_to_local_single_tenant() -> None:
    configuration = load_runtime_security_configuration({})

    assert configuration.deployment_environment is DeploymentEnvironment.DEVELOPMENT
    assert configuration.tenancy_mode is TenancyMode.LOCAL_SINGLE_TENANT
    assert (
        configuration.authorization_migration_mode
        is AuthorizationMigrationMode.LEGACY_AUTHORITATIVE
    )


def test_production_requires_explicit_tenancy_mode() -> None:
    with pytest.raises(
        RuntimeSecurityConfigurationError,
        match="PM_TENANCY_MODE must be explicitly configured",
    ):
        load_runtime_security_configuration({"PM_DEPLOYMENT_ENV": "production"})


def test_explicit_saas_and_shadow_mode_are_parsed() -> None:
    configuration = load_runtime_security_configuration(
        {
            "PM_DEPLOYMENT_ENV": "production",
            "PM_TENANCY_MODE": "saas",
            "PM_AUTHORIZATION_MIGRATION_MODE": "canonical_shadow",
        }
    )

    assert configuration.deployment_environment is DeploymentEnvironment.PRODUCTION
    assert configuration.tenancy_mode is TenancyMode.SAAS
    assert (
        configuration.authorization_migration_mode
        is AuthorizationMigrationMode.CANONICAL_SHADOW
    )


@pytest.mark.parametrize(
    ("variable", "value"),
    (
        ("PM_DEPLOYMENT_ENV", "staging"),
        ("PM_TENANCY_MODE", "automatic"),
        ("PM_AUTHORIZATION_MIGRATION_MODE", "fallback"),
    ),
)
def test_invalid_security_configuration_fails_fast(
    variable: str,
    value: str,
) -> None:
    values = {
        "PM_DEPLOYMENT_ENV": "test",
        "PM_TENANCY_MODE": "local_single_tenant",
        "PM_AUTHORIZATION_MIGRATION_MODE": "LEGACY_AUTHORITATIVE",
        variable: value,
    }

    with pytest.raises(RuntimeSecurityConfigurationError, match=variable):
        load_runtime_security_configuration(values)


def test_saas_policy_never_uses_default_tenant_without_session_context() -> None:
    tenant = Tenant.create(tenant_code="ACME", display_name="Acme")
    repository = _TenantRepository(tenant)

    resolved = SaaSTenantContextPolicy().resolve_active_tenant(
        session_tenant_id=None,
        tenant_repo=repository,
    )

    assert resolved is None


def test_local_policy_uses_default_tenant_without_session_context() -> None:
    tenant = Tenant.create(tenant_code="LOCAL", display_name="Local")
    repository = _TenantRepository(tenant)

    resolved = LocalSingleTenantContextPolicy().resolve_active_tenant(
        session_tenant_id=None,
        tenant_repo=repository,
    )

    assert resolved == tenant


def test_tenant_context_service_delegates_fallback_to_policy() -> None:
    tenant = Tenant.create(tenant_code="ACME", display_name="Acme")
    repository = _TenantRepository(tenant)
    service = TenantContextService(
        tenant_repo=repository,
        organization_repo=_OrganizationRepository(),
        user_session=UserSessionContext(),
        context_policy=SaaSTenantContextPolicy(),
    )

    assert service.get_active_tenant() is None
