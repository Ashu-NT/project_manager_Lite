from __future__ import annotations

from typing import Protocol

from src.core.shared.events.domain_event import DomainEvent


class LinkedEmployeeResource(Protocol):
    id: str
    name: str
    role: str
    contact: str
    worker_type: object | None
    employee_id: str | None
    organization_id: str | None
    version: int


class ResourceMasterEventFactory(Protocol):
    """Builds the business-module-owned event for one resource touched by an Employee sync.
    Platform never imports the concrete Resource event class -- composition supplies the
    concrete builder, and this Protocol is the only shape Platform code depends on."""

    def __call__(
        self, resource: LinkedEmployeeResource, *, tenant_id: str, organization_id: str
    ) -> DomainEvent: ...


__all__ = ["LinkedEmployeeResource", "ResourceMasterEventFactory"]
