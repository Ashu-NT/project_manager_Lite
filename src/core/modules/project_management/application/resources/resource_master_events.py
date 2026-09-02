from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ResourceMasterChangeType(str, Enum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    DEACTIVATED = "DEACTIVATED"
    REACTIVATED = "REACTIVATED"
    PURGED = "PURGED"


@dataclass(frozen=True, slots=True)
class ResourceMasterChanged:
    """A canonical DomainEvent -- recorded via `uow.record_event(...)` and dispatched
    through the shared transactional/post-commit pipeline, never a bespoke `Signal[T]`."""

    tenant_id: str
    organization_id: str
    resource_id: str
    version: int
    change_type: ResourceMasterChangeType


def build_resource_master_changed_for_employee_sync(
    resource, *, tenant_id: str, organization_id: str
) -> ResourceMasterChanged:
    """The concrete `ResourceMasterEventFactory` (P18A §8) wired into `EmployeeService` at
    composition -- Platform's `employee_service.py` never imports this module directly; it only
    depends on the Platform-owned `ResourceMasterEventFactory` Protocol this function satisfies
    structurally. `resource` is the touched `LinkedEmployeeResource` returned by
    `sync_linked_employee_resources`, already carrying its post-update `version`."""
    return ResourceMasterChanged(
        tenant_id=tenant_id,
        organization_id=organization_id,
        resource_id=resource.id,
        version=resource.version,
        change_type=ResourceMasterChangeType.UPDATED,
    )


__all__ = [
    "ResourceMasterChangeType",
    "ResourceMasterChanged",
    "build_resource_master_changed_for_employee_sync",
]
