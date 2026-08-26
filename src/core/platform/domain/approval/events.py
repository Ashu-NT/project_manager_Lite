from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ApprovalRequested:
    approval_id: str
    tenant_id: str
    organization_id: str | None
    approval_type: str
    entity_type: str
    entity_id: str
    requested_by_user_id: str | None
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ApprovalApproved:
    approval_id: str
    tenant_id: str
    organization_id: str | None
    approval_type: str
    entity_type: str
    entity_id: str
    decided_by_user_id: str | None
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ApprovalRejected:
    approval_id: str
    tenant_id: str
    organization_id: str | None
    approval_type: str
    entity_type: str
    entity_id: str
    decided_by_user_id: str | None
    occurred_at: datetime


__all__ = ["ApprovalRequested", "ApprovalApproved", "ApprovalRejected"]
