from __future__ import annotations

from typing import Any

from src.core.modules.project_management.domain.enums import WorkerType
from src.ui_qml.modules.project_management.view_models.resources import (
    ResourceDetailFieldViewModel,
    ResourceDetailViewModel,
    ResourceInspectorViewModel,
)


def build_resource_state(resource: Any) -> dict[str, object]:
    return {
        "resourceId": resource.id,
        "name": resource.name,
        "resourceCode": resource.code,
        "role": resource.role,
        "workerType": resource.worker_type,
        "workerTypeLabel": resource.worker_type_label,
        "costType": resource.cost_type,
        "costTypeLabel": resource.cost_type_label,
        "hourlyRate": resource.hourly_rate,
        "hourlyRateLabel": resource.hourly_rate_label,
        "currency": resource.currency_code or "",
        "capacityPercent": f"{resource.capacity_percent:.1f}",
        "capacityLabel": resource.capacity_label,
        "address": resource.address,
        "contact": resource.contact,
        "organizationId": resource.organization_id,
        "organization": resource.organization_label,
        "departmentId": resource.department_id or "",
        "department": resource.department,
        "siteId": resource.site_id or "",
        "site": resource.site,
        "employeeId": resource.employee_id or "",
        "employeeName": resource.employee_name,
        "employeeContext": resource.employee_context,
        "isActive": resource.is_active,
        "activeLabel": resource.active_label,
        "version": resource.version,
        "canRead": resource.can_read,
        "canManage": resource.can_manage,
    }


def build_detail_view_model(resource: Any) -> ResourceDetailViewModel:
    state = build_resource_state(resource)
    subtitle = " | ".join(
        value
        for value in (resource.role, resource.organization_label, resource.department)
        if value
    ) or resource.worker_type_label
    description = (
        "Employee-linked resource. Platform identity remains authoritative."
        if resource.worker_type == WorkerType.EMPLOYEE.value
        else "External PM resource available for scoped project planning."
    )
    return ResourceDetailViewModel(
        id=resource.id,
        title=resource.name,
        status_label=resource.active_label,
        subtitle=subtitle,
        description=description,
        fields=(
            ResourceDetailFieldViewModel("Code", resource.code or "-"),
            ResourceDetailFieldViewModel("Worker type", resource.worker_type_label),
            ResourceDetailFieldViewModel("Role", resource.role or "-"),
            ResourceDetailFieldViewModel("Organization", resource.organization_label or "-"),
            ResourceDetailFieldViewModel("Department", resource.department or "-"),
            ResourceDetailFieldViewModel("Site", resource.site or "-"),
            ResourceDetailFieldViewModel("Capacity modifier", resource.capacity_label),
            ResourceDetailFieldViewModel("Version", str(resource.version)),
        ),
        state=state,
    )


def build_inspector_view_model(resource: Any) -> ResourceInspectorViewModel:
    state = {
        "resourceId": resource.id,
        "version": resource.version,
        "canRead": resource.can_read,
        "canManage": resource.can_manage,
        "canDeactivate": resource.can_deactivate,
        "canReactivate": resource.can_reactivate,
    }
    return ResourceInspectorViewModel(
        id=resource.id,
        title=resource.name,
        status_label=resource.active_label,
        fields=(
            ResourceDetailFieldViewModel("Code", resource.code or "-"),
            ResourceDetailFieldViewModel("Role", resource.role or "-"),
            ResourceDetailFieldViewModel("Engagement", resource.worker_type_label),
            ResourceDetailFieldViewModel("Organization", resource.organization_label or "-"),
            ResourceDetailFieldViewModel("Department", resource.department or "-"),
            ResourceDetailFieldViewModel("Site", resource.site or "-"),
            ResourceDetailFieldViewModel("Capacity modifier", resource.capacity_label),
            ResourceDetailFieldViewModel("Active projects", str(resource.project_count)),
            ResourceDetailFieldViewModel("Assignments", str(resource.assignment_count)),
        ),
        state=state,
    )


__all__ = [
    "build_detail_view_model",
    "build_inspector_view_model",
    "build_resource_state",
]
