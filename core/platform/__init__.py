from core.platform.modules import ModuleGuardedServiceMixin, require_module_enabled
from core.platform.modules import ModuleEntitlementRecord, ModuleEntitlementRepository
from core.platform.modules import (
    DEFAULT_PLATFORM_CAPABILITIES,
    DEFAULT_ENTERPRISE_MODULES,
    ModuleCatalogEntry,
    ModuleCatalogService,
    ModuleEntitlement,
    ModuleRuntimeService,
    ModuleRuntimeSnapshot,
    PlatformCapability,
    SupportsModuleEntitlements,
    build_default_module_catalog,
    parse_enabled_module_codes,
    parse_licensed_module_codes,
    resolve_module_runtime_service,
)

__all__ = [
    "DEFAULT_PLATFORM_CAPABILITIES",
    "DEFAULT_ENTERPRISE_MODULES",
    "ModuleCatalogEntry",
    "ModuleCatalogService",
    "ModuleEntitlement",
    "ModuleEntitlementRecord",
    "ModuleEntitlementRepository",
    "ModuleGuardedServiceMixin",
    "ModuleRuntimeService",
    "ModuleRuntimeSnapshot",
    "PlatformCapability",
    "SupportsModuleEntitlements",
    "build_default_module_catalog",
    "parse_enabled_module_codes",
    "parse_licensed_module_codes",
    "resolve_module_runtime_service",
    "require_module_enabled",
]
