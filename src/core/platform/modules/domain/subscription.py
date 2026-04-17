from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModuleEntitlementRecord:
    module_code: str
    licensed: bool
    enabled: bool
    lifecycle_status: str = "inactive"


__all__ = ["ModuleEntitlementRecord"]
