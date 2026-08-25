from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


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
    "TenantMembershipActivated",
    "TenantMembershipReactivated",
    "TenantMembershipRemoved",
    "TenantMembershipSuspended",
]
