from core.platform.modules.contracts import SupportsModuleEntitlements
from core.platform.modules.authorization import require_module_enabled
from core.platform.modules.guard import ModuleGuardedServiceMixin
from core.platform.modules.repository import ModuleEntitlementRecord, ModuleEntitlementRepository
from core.platform.modules.runtime import (
    ModuleRuntimeService,
    ModuleRuntimeSnapshot,
    resolve_module_runtime_service,
)
from core.platform.modules.service import (
    DEFAULT_PLATFORM_CAPABILITIES,
    DEFAULT_ENTERPRISE_MODULES,
    ModuleCatalogEntry,
    ModuleCatalogService,
    ModuleEntitlement,
    PlatformCapability,
    build_default_module_catalog,
    parse_enabled_module_codes,
    parse_licensed_module_codes,
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
