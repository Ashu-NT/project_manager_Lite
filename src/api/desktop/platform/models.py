from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar

_ResultT = TypeVar("_ResultT")


@dataclass(frozen=True)
class DesktopApiError:
    code: str
    message: str
    category: str


@dataclass(frozen=True)
class DesktopApiResult(Generic[_ResultT]):
    ok: bool
    data: _ResultT | None = None
    error: DesktopApiError | None = None


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
class OrganizationDto:
    id: str
    organization_code: str
    display_name: str
    timezone_name: str
    base_currency: str
    is_active: bool
    version: int


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


@dataclass(frozen=True)
class OrganizationProvisionCommand:
    organization_code: str
    display_name: str
    timezone_name: str
    base_currency: str
    is_active: bool = True
    initial_module_codes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class OrganizationUpdateCommand:
    organization_id: str
    organization_code: str | None = None
    display_name: str | None = None
    timezone_name: str | None = None
    base_currency: str | None = None
    is_active: bool | None = None
    expected_version: int | None = None

