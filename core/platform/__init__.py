from core.platform.modules import ModuleGuardedServiceMixin, require_module_enabled
from core.platform.modules import ModuleEntitlementRecord, ModuleEntitlementRepository
from core.platform.time import TimeEntry, TimeEntryRepository, TimeService, TimesheetPeriod, TimesheetPeriodRepository, TimesheetPeriodStatus, WorkEntry
from core.platform.modules import (
    DEFAULT_PLATFORM_CAPABILITIES,
    DEFAULT_ENTERPRISE_MODULES,
    ModuleCatalogEntry,
    ModuleCatalogService,
    ModuleEntitlement,
    PlatformCapability,
    SupportsModuleEntitlements,
    build_default_module_catalog,
    normalize_module_code,
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
    "PlatformCapability",
    "SupportsModuleEntitlements",
    "TimeEntry",
    "TimeEntryRepository",
    "TimeService",
    "TimesheetPeriod",
    "TimesheetPeriodRepository",
    "TimesheetPeriodStatus",
    "WorkEntry",
    "build_default_module_catalog",
    "normalize_module_code",
    "parse_enabled_module_codes",
    "parse_licensed_module_codes",
    "require_module_enabled",
]
