from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ResourceCapabilityChangeType(str, Enum):
    ADDED = "ADDED"
    UPDATED = "UPDATED"
    REMOVED = "REMOVED"


@dataclass(frozen=True, slots=True)
class ResourceCapabilityChanged:
    """A canonical DomainEvent (P18A) -- recorded via `uow.record_event(...)` and dispatched
    through the shared transactional/post-commit pipeline, never a bespoke `Signal[T]`."""

    tenant_id: str
    organization_id: str
    resource_id: str
    child_id: str
    child_version: int
    child_type: str
    change_type: ResourceCapabilityChangeType


__all__ = [
    "ResourceCapabilityChanged",
    "ResourceCapabilityChangeType",
]
