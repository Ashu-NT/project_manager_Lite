from __future__ import annotations

from dataclasses import dataclass

from src.core.platform.application.master_data.org.dto.responses.organization import (
    OrganizationDto,
)
from src.core.platform.application.platform_runtime.dto.responses.module_runtime import (
    RuntimeModuleFact,
    RuntimePlatformCapabilityFact,
)


@dataclass(frozen=True)
class ModuleEntitlementDto:
    module_code: str
    label: str
    stage: str
    licensed: bool
    enabled: bool
    runtime_enabled: bool
    lifecycle_status: str
    lifecycle_label: str
    lifecycle_alert: str | None
    available_to_license: bool
    planned: bool
    module: RuntimeModuleFact


@dataclass(frozen=True)
class PlatformRuntimeContextDto:
    context_label: str
    shell_summary: str
    active_organization: OrganizationDto | None
    platform_capabilities: tuple[RuntimePlatformCapabilityFact, ...]
    entitlements: tuple[ModuleEntitlementDto, ...]
    enabled_modules: tuple[RuntimeModuleFact, ...]
    licensed_modules: tuple[RuntimeModuleFact, ...]
    available_modules: tuple[RuntimeModuleFact, ...]
    planned_modules: tuple[RuntimeModuleFact, ...]
