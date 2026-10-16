from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class ResourceMasterChangeType(str, Enum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    DEACTIVATED = "DEACTIVATED"
    REACTIVATED = "REACTIVATED"
    PURGED = "PURGED"


@dataclass(frozen=True, slots=True)
class ResourceMasterChanged:
    tenant_id: str
    organization_id: str
    resource_id: str
    version: int
    change_type: ResourceMasterChangeType
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


__all__ = [
    "ResourceMasterChangeType",
    "ResourceMasterChanged",
]
