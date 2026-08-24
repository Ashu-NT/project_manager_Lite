from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.core.shared.events.signal import Signal


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


resource_master_changed: Signal[ResourceMasterChanged] = Signal()


__all__ = [
    "ResourceMasterChangeType",
    "ResourceMasterChanged",
    "resource_master_changed",
]
