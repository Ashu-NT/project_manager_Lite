from __future__ import annotations

from typing import Protocol

from src.core.platform.domain.tenant.modules.module_entitlement import ModuleEntitlement


class SupportsModuleEntitlements(Protocol):
    def get_entitlement(self, module_code: str) -> ModuleEntitlement | None: ...

    def is_enabled(self, module_code: str) -> bool: ...


__all__ = ["SupportsModuleEntitlements"]
