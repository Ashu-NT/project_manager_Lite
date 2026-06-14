from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.shared.audit import record_audit_entry

if TYPE_CHECKING:
    from src.core.platform.department.domain import Department
    from src.core.platform.org.domain import Organization

    from .department_service import DepartmentService


def record_department_create(service: DepartmentService, department: Department, organization: Organization) -> None:
    record_audit_entry(
        service,
        operation="create",
        entity_type="department",
        entity_id=department.id,
        module="platform",
        severity="low",
        metadata={
            "action": "department.create",
            "organization_id": organization.id,
            "department_code": department.department_code,
            "name": department.name,
            "site_id": department.site_id or "",
            "default_location_id": department.default_location_id or "",
            "department_type": department.department_type,
            "is_active": str(department.is_active),
        },
    )


def record_department_update(service: DepartmentService, department: Department, organization: Organization) -> None:
    record_audit_entry(
        service,
        operation="update",
        entity_type="department",
        entity_id=department.id,
        module="platform",
        severity="low",
        metadata={
            "action": "department.update",
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
