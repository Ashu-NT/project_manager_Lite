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
    """Builds the business-module-owned typed event for one resource touched by an Employee
    sync (P18A §8). Platform never imports the concrete Resource event class -- the concrete
    builder is supplied by composition (ADR-005 Sec21/Sec22: no new Platform -> business-module
    import), so this Protocol is the only shape Platform code depends on."""

    def __call__(
        self, resource: LinkedEmployeeResource, *, tenant_id: str, organization_id: str
    ) -> DomainEvent: ...


__all__ = ["LinkedEmployeeResource", "ResourceMasterEventFactory"]
