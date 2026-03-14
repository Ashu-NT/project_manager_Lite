from __future__ import annotations

from functools import wraps

from core.platform.modules.authorization import require_module_enabled


def _humanize_method_name(name: str) -> str:
    return name.replace("_", " ").strip() or "use this service"


class ModuleGuardedServiceMixin:
    _module_guard_code: str | None = None
    _module_guard_exempt_methods: frozenset[str] = frozenset()

    def __getattribute__(self, name: str):
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
        def _guarded(*args, **kwargs):
            require_module_enabled(
                getattr(self, "_module_catalog_service", None),
                module_code,
                operation_label=_humanize_method_name(name),
            )
            return attr(*args, **kwargs)

        return _guarded


__all__ = ["ModuleGuardedServiceMixin"]
