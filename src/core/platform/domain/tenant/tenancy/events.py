from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass(frozen=True, slots=True, kw_only=True)
class TenantInvitationChanged:
    membership_id: str
    tenant_id: str
    recipient_user_id: str
    change_type: str
    occurred_at: datetime
    event_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True, slots=True, kw_only=True)
class TenantMembershipActivated:
    membership_id: str
    tenant_id: str
    user_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class TenantMembershipSuspended:
    membership_id: str
    tenant_id: str
    user_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class TenantMembershipReactivated:
    membership_id: str
    tenant_id: str
    user_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class TenantMembershipRemoved:
    membership_id: str
    tenant_id: str
    user_id: str
    occurred_at: datetime


__all__ = [
    "TenantInvitationChanged",
    "TenantMembershipActivated",
    "TenantMembershipReactivated",
    "TenantMembershipRemoved",
    "TenantMembershipSuspended",
]
