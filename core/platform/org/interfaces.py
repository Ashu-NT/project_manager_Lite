from __future__ import annotations

from typing import Protocol


class LinkedEmployeeResource(Protocol):
    id: str
    name: str
    role: str
    contact: str
    worker_type: object | None
    employee_id: str | None


class LinkedEmployeeResourceRepository(Protocol):
    def list_by_employee(self, employee_id: str) -> list[LinkedEmployeeResource]: ...

    def update(self, resource: LinkedEmployeeResource) -> None: ...

class LocationReference(Protocol):
    id: str
    organization_id: str
    site_id: str
    location_code: str
    name: str
    is_active: bool


class LocationReferenceRepository(Protocol):
    def get(self, location_id: str) -> LocationReference | None: ...

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
    ) -> list[LocationReference]: ...


__all__ = [
    "LinkedEmployeeResource",
    "LinkedEmployeeResourceRepository",
    "LocationReference",
    "LocationReferenceRepository",
]
