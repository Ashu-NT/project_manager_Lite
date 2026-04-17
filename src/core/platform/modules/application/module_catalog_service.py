from __future__ import annotations

import os
from typing import Callable, Iterable

from sqlalchemy.orm import Session

from core.platform.org.domain import Organization
from src.core.platform.modules.application.module_catalog_context import (
    ModuleCatalogContextMixin,
)
from src.core.platform.modules.application.module_catalog_mutation import (
    ModuleCatalogMutationMixin,
)
from src.core.platform.modules.application.module_catalog_query import ModuleCatalogQueryMixin
from src.core.platform.modules.contracts import ModuleEntitlementRepository
from src.core.platform.modules.domain import (
    DEFAULT_ENTERPRISE_MODULES,
    DEFAULT_PLATFORM_CAPABILITIES,
    MODULE_LIFECYCLE_ACTIVE,
    MODULE_LIFECYCLE_EXPIRED,
    MODULE_LIFECYCLE_INACTIVE,
    MODULE_LIFECYCLE_STATUSES,
    MODULE_LIFECYCLE_SUSPENDED,
    MODULE_LIFECYCLE_TRIAL,
    MODULE_RUNTIME_ACCESS_STATUSES,
    EnterpriseModule,
    ModuleCatalogSnapshot,
    ModuleEntitlement,
    PlatformCapability,
    parse_enabled_module_codes,
    parse_licensed_module_codes,
    parse_module_codes,
)
from src.core.platform.modules.domain.module_codes import normalize_module_code


class ModuleCatalogService(
    ModuleCatalogMutationMixin,
    ModuleCatalogQueryMixin,
    ModuleCatalogContextMixin,
):
    def __init__(
        self,
        *,
        modules: Iterable[EnterpriseModule],
        enabled_codes: Iterable[str] | None,
        licensed_codes: Iterable[str] | None = None,
        platform_capabilities: Iterable[PlatformCapability] | None = None,
        entitlement_repo: ModuleEntitlementRepository | None = None,
        session: Session | None = None,
        user_session=None,
        audit_service=None,
        organization_context_provider: Callable[[], Organization | None] | None = None,
    ) -> None:
        known_modules = tuple(modules)
        known_codes = {module.code for module in known_modules}
        default_codes = {
            module.code
            for module in known_modules
            if module.default_enabled
        }
        licensed = (
            {normalize_module_code(code) for code in licensed_codes if str(code).strip()}
            if licensed_codes is not None
            else set(default_codes)
        )
        enabled = (
            {normalize_module_code(code) for code in enabled_codes if str(code).strip()}
            if enabled_codes is not None
            else set(licensed)
        )
        self._modules = known_modules
        self._platform_capabilities = tuple(platform_capabilities or DEFAULT_PLATFORM_CAPABILITIES)
        self._licensed_codes = set(code for code in licensed if code in known_codes)
        self._enabled_codes = set(code for code in enabled if code in self._licensed_codes)
        self._entitlement_repo = entitlement_repo
        self._session = session
        self._user_session = user_session
        self._audit_service = audit_service
        self._organization_context_provider = organization_context_provider


def build_default_module_catalog(
    raw_enabled_modules: str | None = None,
    raw_licensed_modules: str | None = None,
) -> ModuleCatalogService:
    resolved_enabled_raw = (
        raw_enabled_modules if raw_enabled_modules is not None else os.getenv("PM_ENABLED_MODULES")
    )
    resolved_licensed_raw = (
        raw_licensed_modules
        if raw_licensed_modules is not None
        else (
            raw_enabled_modules
            if raw_enabled_modules is not None
            else (
                os.getenv("PM_LICENSED_MODULES")
                if os.getenv("PM_LICENSED_MODULES") is not None
                else resolved_enabled_raw
            )
        )
    )
    return ModuleCatalogService(
        modules=DEFAULT_ENTERPRISE_MODULES,
        enabled_codes=parse_enabled_module_codes(
            resolved_enabled_raw if resolved_enabled_raw is not None else resolved_licensed_raw
        ),
        licensed_codes=parse_licensed_module_codes(resolved_licensed_raw),
    )


ModuleCatalogEntry = EnterpriseModule


__all__ = [
    "DEFAULT_PLATFORM_CAPABILITIES",
    "DEFAULT_ENTERPRISE_MODULES",
    "EnterpriseModule",
    "ModuleCatalogEntry",
    "ModuleCatalogService",
    "ModuleCatalogSnapshot",
    "ModuleEntitlement",
    "MODULE_LIFECYCLE_ACTIVE",
    "MODULE_LIFECYCLE_EXPIRED",
    "MODULE_LIFECYCLE_INACTIVE",
    "MODULE_LIFECYCLE_STATUSES",
    "MODULE_LIFECYCLE_SUSPENDED",
    "MODULE_LIFECYCLE_TRIAL",
    "MODULE_RUNTIME_ACCESS_STATUSES",
    "PlatformCapability",
    "build_default_module_catalog",
    "normalize_module_code",
    "parse_enabled_module_codes",
    "parse_licensed_module_codes",
    "parse_module_codes",
]
