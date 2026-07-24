from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from src.core.platform.common.ids import generate_id


@dataclass
class UserTenantMembership:
    id: str
    user_id: str
    tenant_id: str
    is_active: bool = True
    tenant_role: str = "member"
    invited_at: datetime | None = None
    joined_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @staticmethod
    def create(
        user_id: str,
        tenant_id: str,
        *,
        tenant_role: str = "member",
        is_active: bool = True,
    ) -> "UserTenantMembership":
        now = datetime.now(timezone.utc)
        return UserTenantMembership(
            id=generate_id(),
            user_id=user_id,
            tenant_id=tenant_id,
            is_active=is_active,
            tenant_role=tenant_role,
            invited_at=None,
            joined_at=now,
            created_at=now,
            updated_at=now,
        )


__all__ = ["UserTenantMembership"]
