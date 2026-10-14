from __future__ import annotations

from functools import wraps

from src.core.platform.application.tenant.modules.authorization import (
    require_module_enabled,
)
from src.core.platform.contract.port.tenant.modules.supports_module_entitlements import (
    SupportsModuleEntitlements,
)


def _humanize_method_name(name: str) -> str:
    return name.replace("_", " ").strip() or "use this service"


class ModuleGuardedServiceMixin:
    """Stateless module-entitlement guard policy. Hosts provide `_module_catalog_service`
    (the "is module enabled" capability); a host without one is never blocked."""

    _module_catalog_service: SupportsModuleEntitlements | None
    _module_guard_code: str | None = None
    _module_guard_exempt_methods: frozenset[str] = frozenset()

    def __getattribute__(self, name: str) -> object:
        attr = super().__getattribute__(name)
        if name.startswith("_"):
            return attr
        if not callable(attr):
            return attr
        exempt_methods = super().__getattribute__("_module_guard_exempt_methods")
        if name in exempt_methods:
            return attr
        module_code = super().__getattribute__("_module_guard_code")
        if not module_code:
            return attr

        @wraps(attr)
        def _guarded(*args: object, **kwargs: object) -> object:
            require_module_enabled(
                getattr(self, "_module_catalog_service", None),
                module_code,
                operation_label=_humanize_method_name(name),
            )
            return attr(*args, **kwargs)

        return _guarded


__all__ = ["ModuleGuardedServiceMixin"]
