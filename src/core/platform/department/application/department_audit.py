from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.platform.audit.helpers import record_audit

if TYPE_CHECKING:
    from src.core.platform.department.domain import Department
    from src.core.platform.org.domain import Organization


def record_department_create(service, department: Department, organization: Organization) -> None:
    record_audit(
        service,
        action="department.create",
        entity_type="department",
        entity_id=department.id,
        details={
            "organization_id": organization.id,
            "department_code": department.department_code,
            "name": department.name,
            "site_id": department.site_id or "",
            "default_location_id": department.default_location_id or "",
            "department_type": department.department_type,
            "is_active": str(department.is_active),
        },
    )


def record_department_update(service, department: Department, organization: Organization) -> None:
    record_audit(
        service,
        action="department.update",
        entity_type="department",
        entity_id=department.id,
        details={
            "organization_id": organization.id,
            "department_code": department.department_code,
            "name": department.name,
            "site_id": department.site_id or "",
            "default_location_id": department.default_location_id or "",
            "department_type": department.department_type,
            "is_active": str(department.is_active),
        },
    )


__all__ = ["record_department_create", "record_department_update"]
