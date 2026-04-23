from __future__ import annotations

from dataclasses import dataclass

from src.api.desktop.platform.models.organization import OrganizationDto


@dataclass(frozen=True)
class PlatformCapabilityDto:
    code: str
    label: str
    description: str
    always_on: bool


@dataclass(frozen=True)
class ModuleDto:
    code: str
    label: str
    description: str
    default_enabled: bool
    stage: str
    primary_capabilities: tuple[str, ...]


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
    module: ModuleDto


@dataclass(frozen=True)
class PlatformRuntimeContextDto:
    context_label: str
    shell_summary: str
    active_organization: OrganizationDto | None
    platform_capabilities: tuple[PlatformCapabilityDto, ...]
    entitlements: tuple[ModuleEntitlementDto, ...]
    enabled_modules: tuple[ModuleDto, ...]
    licensed_modules: tuple[ModuleDto, ...]
    available_modules: tuple[ModuleDto, ...]
    planned_modules: tuple[ModuleDto, ...]


@dataclass(frozen=True)
class ModuleStatePatchCommand:
    module_code: str
    licensed: bool | None = None
    enabled: bool | None = None
    lifecycle_status: str | None = None
