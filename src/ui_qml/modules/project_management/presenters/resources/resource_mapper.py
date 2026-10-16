from __future__ import annotations

from src.core.modules.project_management.api.desktop.resources.formatters.enum_formatter import (
    format_enum_label,
)
from src.core.modules.project_management.contracts.reads.resources.models import (
    ResourceCatalogReadItem,
)
from src.ui_qml.modules.project_management.view_models.resources import (
    ResourceRecordViewModel,
)


def to_resource_record_view_model(
    resource: ResourceCatalogReadItem,
) -> ResourceRecordViewModel:
    worker_type_label = format_enum_label(resource.worker_type)
    active_label = "Active" if resource.is_active else "Inactive"
    capacity_label = f"{resource.capacity_percent:.1f}%"
    state = {
        "resourceId": resource.resource_id,
        "resourceCode": resource.code,
        "role": resource.role,
        "kind": resource.kind,
        "kindLabel": format_enum_label(resource.kind),
        "workerType": resource.worker_type,
        "workerTypeLabel": worker_type_label,
        "costType": resource.cost_type,
        "costTypeLabel": format_enum_label(resource.cost_type),
        "organizationId": resource.organization_id,
        "organization": resource.organization_label,
        "departmentId": resource.department_id or "",
        "department": resource.department_label,
        "siteId": resource.site_id or "",
        "site": resource.site_label,
        "employeeId": resource.employee_id or "",
        "employeeName": resource.employee_name,
        "isActive": resource.is_active,
        "activeLabel": active_label,
        "capacityPercent": resource.capacity_percent,
        "capacityLabel": capacity_label,
        "version": resource.version,
    }
    subtitle = (
        " | ".join(value for value in (resource.role, worker_type_label) if value)
        or "No role assigned"
    )
    context = " | ".join(
        value
        for value in (
            resource.organization_label,
            resource.department_label,
            resource.site_label,
        )
        if value
    )
    return ResourceRecordViewModel(
        id=resource.resource_id,
        title=resource.name,
        status_label=active_label,
        subtitle=subtitle,
        supporting_text=f"Capacity modifier {capacity_label}",
        meta_text=context,
        state=state,
    )


__all__ = ["to_resource_record_view_model"]
