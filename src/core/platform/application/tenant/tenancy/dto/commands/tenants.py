from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TenantCreateCommand:
    tenant_code: str
    display_name: str
