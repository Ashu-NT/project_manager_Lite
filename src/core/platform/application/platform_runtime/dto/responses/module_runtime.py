from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RuntimePlatformCapabilityFact:
    code: str
    label: str
    description: str
    always_on: bool


@dataclass(frozen=True, slots=True)
class RuntimeModuleFact:
    code: str
    label: str
    description: str
    default_enabled: bool
    stage: str
    primary_capabilities: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RuntimeEntitlementFact:
    module: RuntimeModuleFact
    code: str
    label: str
    stage: str
    licensed: bool
    enabled: bool
    runtime_enabled: bool
    lifecycle_status: str
    lifecycle_label: str
    lifecycle_alert: bool
    available_to_license: bool
    planned: bool


@dataclass(frozen=True, slots=True)
class ModuleRuntimeSnapshot:
    platform_capabilities: tuple[RuntimePlatformCapabilityFact, ...]
    entitlements: tuple[RuntimeEntitlementFact, ...]
    enabled_modules: tuple[RuntimeModuleFact, ...]
    licensed_modules: tuple[RuntimeModuleFact, ...]
    available_modules: tuple[RuntimeModuleFact, ...]
    planned_modules: tuple[RuntimeModuleFact, ...]
    shell_summary: str
    context_label: str
