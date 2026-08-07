from src.core.platform.application.tenant.modules.authorization import require_module_enabled
from src.core.platform.application.tenant.modules.guard import ModuleGuardedServiceMixin
from src.core.platform.application.tenant.modules.module_catalog_service import (
    ModuleCatalogEntry,
    ModuleCatalogService,
    build_default_module_catalog,
)

__all__ = [
    "ModuleCatalogEntry",
    "ModuleCatalogService",
    "ModuleGuardedServiceMixin",
    "build_default_module_catalog",
    "require_module_enabled",
]
