from src.core.platform.application.tenant.modules.authorization import (
    require_module_enabled,
)
from src.core.platform.application.tenant.modules.guard import ModuleGuardedServiceMixin
from src.core.platform.application.tenant.modules.module_catalog_context import (
    ModuleCatalogContext,
)
from src.core.platform.application.tenant.modules.module_catalog_queries import (
    ModuleCatalogQueryHandler,
    build_default_module_catalog,
)
from src.core.platform.application.tenant.modules.module_entitlement_commands import (
    ModuleEntitlementCommandHandler,
)
from src.core.platform.application.tenant.modules.module_entitlement_provisioning import (
    ModuleEntitlementProvisioningHandler,
)

__all__ = [
    "ModuleCatalogContext",
    "ModuleCatalogQueryHandler",
    "ModuleEntitlementCommandHandler",
    "ModuleEntitlementProvisioningHandler",
    "ModuleGuardedServiceMixin",
    "build_default_module_catalog",
    "require_module_enabled",
]
