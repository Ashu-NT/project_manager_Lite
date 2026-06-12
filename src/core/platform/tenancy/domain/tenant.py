from __future__ import annotations

from dataclasses import dataclass

from src.core.platform.common.ids import generate_id


@dataclass
class Tenant:
    id: str
    tenant_code: str
    display_name: str
    is_active: bool = True
    version: int = 1

    @staticmethod
    def create(
        tenant_code: str,
        display_name: str,
        *,
        is_active: bool = True,
    ) -> "Tenant":
        return Tenant(
            id=generate_id(),
            tenant_code=str(tenant_code or "").strip().upper(),
            display_name=str(display_name or "").strip(),
            is_active=is_active,
            version=1,
        )


__all__ = ["Tenant"]
