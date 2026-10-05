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
    tenant_id: str
    organization_id: str
    resource_id: str
    version: int
    change_type: ResourceMasterChangeType


def build_resource_master_changed_for_employee_sync(
    resource, *, tenant_id: str, organization_id: str
) -> ResourceMasterChanged:
    """Wired into `EmployeeService` at composition, satisfying its
    `ResourceMasterEventFactory` Protocol -- Platform never imports this
    module directly. `resource` is the touched `LinkedEmployeeResource`."""
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
