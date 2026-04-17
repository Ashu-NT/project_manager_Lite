from __future__ import annotations

from dataclasses import dataclass

from src.core.platform.modules import (
    EnterpriseModule,
    ModuleCatalogService,
    ModuleEntitlement,
    PlatformCapability,
)


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


class ModuleRuntimeService:
    """Runtime-facing application seam for module entitlements."""

    def __init__(self, catalog_service: ModuleCatalogService) -> None:
        self._catalog_service = catalog_service

    @property
    def catalog_service(self) -> ModuleCatalogService:
        return self._catalog_service

    def list_modules(self) -> list[EnterpriseModule]:
        return self._catalog_service.list_modules()

    def list_platform_capabilities(self) -> list[PlatformCapability]:
        return self._catalog_service.list_platform_capabilities()

    def list_entitlements(self) -> list[ModuleEntitlement]:
        return self._catalog_service.list_entitlements()

    def list_licensed_modules(self) -> list[EnterpriseModule]:
        return self._catalog_service.list_licensed_modules()

    def list_enabled_modules(self) -> list[EnterpriseModule]:
        return self._catalog_service.list_enabled_modules()

    def list_available_modules(self) -> list[EnterpriseModule]:
        return self._catalog_service.list_available_modules()

    def list_planned_modules(self) -> list[EnterpriseModule]:
        return self._catalog_service.list_planned_modules()

    def enabled_capability_codes(self) -> tuple[str, ...]:
        return self._catalog_service.enabled_capability_codes()

    def is_licensed(self, module_code: str) -> bool:
        return self._catalog_service.is_licensed(module_code)

    def is_enabled(self, module_code: str) -> bool:
        return self._catalog_service.is_enabled(module_code)

    def get_entitlement(self, module_code: str) -> ModuleEntitlement | None:
        return self._catalog_service.get_entitlement(module_code)

    def set_module_state(
        self,
        module_code: str,
        *,
        licensed: bool | None = None,
        enabled: bool | None = None,
        lifecycle_status: str | None = None,
    ) -> ModuleEntitlement:
        return self._catalog_service.set_module_state(
            module_code,
            licensed=licensed,
            enabled=enabled,
            lifecycle_status=lifecycle_status,
        )

    def shell_summary(self) -> str:
        return self._catalog_service.shell_summary()

    def current_context_label(self) -> str:
        return self._catalog_service.current_context_label()

    def snapshot(self) -> ModuleRuntimeSnapshot:
        return ModuleRuntimeSnapshot(
            platform_capabilities=tuple(self.list_platform_capabilities()),
            entitlements=tuple(self.list_entitlements()),
            enabled_modules=tuple(self.list_enabled_modules()),
            licensed_modules=tuple(self.list_licensed_modules()),
            available_modules=tuple(self.list_available_modules()),
            planned_modules=tuple(self.list_planned_modules()),
            shell_summary=self.shell_summary(),
            context_label=self.current_context_label(),
        )


def resolve_module_runtime_service(
    *,
    module_runtime_service: object | None,
    module_catalog_service: ModuleCatalogService | None,
) -> object | None:
    if isinstance(module_runtime_service, ModuleRuntimeService):
        if module_catalog_service is None or module_runtime_service.catalog_service is module_catalog_service:
            return module_runtime_service
    if module_catalog_service is not None:
        return ModuleRuntimeService(module_catalog_service)
    return module_runtime_service


__all__ = ["ModuleRuntimeService", "ModuleRuntimeSnapshot", "resolve_module_runtime_service"]
