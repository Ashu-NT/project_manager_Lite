from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TenantSwitcherItemViewModel:
    id: str
    display_name: str
    tenant_code: str
    tenant_status: str
    is_active: bool


__all__ = ["TenantSwitcherItemViewModel"]
