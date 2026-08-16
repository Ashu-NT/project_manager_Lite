from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TenantDto:
    id: str
    tenant_code: str
    display_name: str
    tenant_status: str
    is_active: bool


@dataclass(frozen=True)
class TenantCreateCommand:
    tenant_code: str
    display_name: str


@dataclass(frozen=True)
class TenantInvitationDto:
    membership_id: str
    tenant_id: str
    status: str
    invited_by_user_id: str | None
    invited_at: datetime
    expires_at: datetime


__all__ = ["TenantCreateCommand", "TenantDto", "TenantInvitationDto"]
