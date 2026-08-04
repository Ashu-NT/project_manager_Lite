from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from src.core.platform.application.tenant.tenancy.context_policy import TenancyMode


class RuntimeSecurityConfigurationError(RuntimeError):
    pass


class DeploymentEnvironment(str, Enum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


@dataclass(frozen=True)
class RuntimeSecurityConfiguration:
    deployment_environment: DeploymentEnvironment
    tenancy_mode: TenancyMode


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
    return RuntimeSecurityConfiguration(
        deployment_environment=deployment_environment,
        tenancy_mode=tenancy_mode,
    )


__all__ = [
    "DeploymentEnvironment",
    "RuntimeSecurityConfiguration",
    "RuntimeSecurityConfigurationError",
    "load_runtime_security_configuration",
]
