from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TenantDto:
    id: str
    tenant_code: str
    display_name: str
    tenant_status: str
    is_active: bool


__all__ = ["TenantDto"]
