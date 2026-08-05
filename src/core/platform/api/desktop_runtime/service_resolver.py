from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from src.core.platform.domain.tenant.modules import (
    EnterpriseModule,
    ModuleEntitlement,
    PlatformCapability,
)
from src.core.platform.application.tenant.modules import ModuleCatalogService


@dataclass(frozen=True)
class ModuleRuntimeSnapshot:
    platform_capabilities: tuple[PlatformCapability, ...]
    entitlements: tuple[ModuleEntitlement, ...]
    enabled_modules: tuple[EnterpriseModule, ...]
    licensed_modules: tuple[EnterpriseModule, ...]
    available_modules: tuple[EnterpriseModule, ...]
    planned_modules: tuple[EnterpriseModule, ...]
    shell_summary: str
    context_label: str


def build_module_runtime_snapshot(catalog_service: ModuleCatalogService) -> ModuleRuntimeSnapshot:
    return ModuleRuntimeSnapshot(
        platform_capabilities=tuple(catalog_service.list_platform_capabilities()),
        entitlements=tuple(catalog_service.list_entitlements()),
        enabled_modules=tuple(catalog_service.list_enabled_modules()),
        licensed_modules=tuple(catalog_service.list_licensed_modules()),
        available_modules=tuple(catalog_service.list_available_modules()),
        planned_modules=tuple(catalog_service.list_planned_modules()),
        shell_summary=catalog_service.shell_summary(),
        context_label=catalog_service.current_context_label(),
    )


def resolve_module_catalog_service(
    services: Mapping[str, object],
) -> ModuleCatalogService | None:
    candidate = services.get("module_catalog_service")
    return candidate if isinstance(candidate, ModuleCatalogService) else None


__all__ = [
    "ModuleRuntimeSnapshot",
    "build_module_runtime_snapshot",
    "resolve_module_catalog_service",
]
