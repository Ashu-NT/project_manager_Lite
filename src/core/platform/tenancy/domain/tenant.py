from __future__ import annotations

from dataclasses import dataclass

from src.core.platform.common.ids import generate_id

TENANT_STATUS_ACTIVE = "active"
TENANT_STATUS_SUSPENDED = "suspended"
TENANT_STATUS_ARCHIVED = "archived"

VALID_TENANT_STATUSES: frozenset[str] = frozenset({
    TENANT_STATUS_ACTIVE,
    TENANT_STATUS_SUSPENDED,
    TENANT_STATUS_ARCHIVED,
})


@dataclass
class Tenant:
    id: str
    tenant_code: str
    display_name: str
    tenant_status: str = TENANT_STATUS_ACTIVE
    version: int = 1

    @property
    def is_active(self) -> bool:
        return self.tenant_status == TENANT_STATUS_ACTIVE

    @staticmethod
    def create(
        tenant_code: str,
        display_name: str,
        *,
        is_active: bool = True,
        tenant_status: str | None = None,
    ) -> "Tenant":
        resolved_status = tenant_status or (TENANT_STATUS_ACTIVE if is_active else TENANT_STATUS_SUSPENDED)
        return Tenant(
            id=generate_id(),
            tenant_code=str(tenant_code or "").strip().upper(),
            display_name=str(display_name or "").strip(),
            tenant_status=resolved_status,
            version=1,
        )


__all__ = [
    "TENANT_STATUS_ACTIVE",
    "TENANT_STATUS_ARCHIVED",
    "TENANT_STATUS_SUSPENDED",
    "VALID_TENANT_STATUSES",
    "Tenant",
]
