from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from src.core.platform.tenancy.context_policy import TenancyMode


class RuntimeSecurityConfigurationError(RuntimeError):
    pass


class DeploymentEnvironment(str, Enum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class AuthorizationMigrationMode(str, Enum):
    # RBAC-TRANSITION-ONLY: Collapse this switch after CANONICAL_ONLY has
    # completed its observation and evidence-retention gates.
    LEGACY_AUTHORITATIVE = "LEGACY_AUTHORITATIVE"
    CANONICAL_SHADOW = "CANONICAL_SHADOW"
    CANONICAL_AUTHORITATIVE = "CANONICAL_AUTHORITATIVE"
    CANONICAL_ONLY = "CANONICAL_ONLY"


OPERATIONAL_AUTHORIZATION_MIGRATION_MODES = frozenset(
    {AuthorizationMigrationMode.LEGACY_AUTHORITATIVE}
)


@dataclass(frozen=True)
class RuntimeSecurityConfiguration:
    deployment_environment: DeploymentEnvironment
    tenancy_mode: TenancyMode
    authorization_migration_mode: AuthorizationMigrationMode


def ensure_operational_authorization_migration_mode(
    mode: AuthorizationMigrationMode,
) -> None:
    if mode in OPERATIONAL_AUTHORIZATION_MIGRATION_MODES:
        return
    raise RuntimeSecurityConfigurationError(
        "PM_AUTHORIZATION_MIGRATION_MODE="
        f"{mode.value} is reserved but not operationally implemented. "
        "Use LEGACY_AUTHORITATIVE until its transition gates are implemented."
    )


def _parse_enum(
    raw_value: str,
    enum_type: type[Enum],
    *,
    variable_name: str,
    uppercase: bool = False,
) -> Enum:
    normalized = str(raw_value or "").strip()
    normalized = normalized.upper() if uppercase else normalized.lower()
    try:
        return enum_type(normalized)
    except ValueError as exc:
        allowed = ", ".join(str(item.value) for item in enum_type)
        raise RuntimeSecurityConfigurationError(
            f"{variable_name} must be one of: {allowed}."
        ) from exc


def load_runtime_security_configuration(
    environ: Mapping[str, str] | None = None,
) -> RuntimeSecurityConfiguration:
    values = os.environ if environ is None else environ
    deployment_environment = _parse_enum(
        values.get("PM_DEPLOYMENT_ENV", DeploymentEnvironment.DEVELOPMENT.value),
        DeploymentEnvironment,
        variable_name="PM_DEPLOYMENT_ENV",
    )
    raw_tenancy_mode = str(values.get("PM_TENANCY_MODE", "") or "").strip()
    if (
        deployment_environment is DeploymentEnvironment.PRODUCTION
        and not raw_tenancy_mode
    ):
        raise RuntimeSecurityConfigurationError(
            "PM_TENANCY_MODE must be explicitly configured in production."
        )
    tenancy_mode = _parse_enum(
        raw_tenancy_mode or TenancyMode.LOCAL_SINGLE_TENANT.value,
        TenancyMode,
        variable_name="PM_TENANCY_MODE",
    )
    authorization_migration_mode = _parse_enum(
        values.get(
            "PM_AUTHORIZATION_MIGRATION_MODE",
            AuthorizationMigrationMode.LEGACY_AUTHORITATIVE.value,
        ),
        AuthorizationMigrationMode,
        variable_name="PM_AUTHORIZATION_MIGRATION_MODE",
        uppercase=True,
    )
    ensure_operational_authorization_migration_mode(
        authorization_migration_mode
    )
    return RuntimeSecurityConfiguration(
        deployment_environment=deployment_environment,
        tenancy_mode=tenancy_mode,
        authorization_migration_mode=authorization_migration_mode,
    )


__all__ = [
    "AuthorizationMigrationMode",
    "DeploymentEnvironment",
    "OPERATIONAL_AUTHORIZATION_MIGRATION_MODES",
    "RuntimeSecurityConfiguration",
    "RuntimeSecurityConfigurationError",
    "ensure_operational_authorization_migration_mode",
    "load_runtime_security_configuration",
]
