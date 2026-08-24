from __future__ import annotations

from typing import Any

from src.ui_qml.modules.project_management.view_models.resources import ResourceRecordViewModel


def to_resource_record_view_model(resource: Any) -> ResourceRecordViewModel:
    state = {
        "resourceId": resource.id,
        "resourceCode": resource.code,
        "role": resource.role,
        "kind": resource.kind,
        "kindLabel": resource.kind_label,
        "workerType": resource.worker_type,
        "workerTypeLabel": resource.worker_type_label,
        "costType": resource.cost_type,
        "costTypeLabel": resource.cost_type_label,
        "organizationId": resource.organization_id,
        "organization": resource.organization_label,
        "departmentId": resource.department_id or "",
        "department": resource.department,
        "siteId": resource.site_id or "",
        "site": resource.site,
        "employeeId": resource.employee_id or "",
        "employeeName": resource.employee_name,
        "isActive": resource.is_active,
        "activeLabel": resource.active_label,
        "capacityPercent": resource.capacity_percent,
        "capacityLabel": resource.capacity_label,
        "version": resource.version,
    }
    subtitle = " | ".join(
        value for value in (resource.role, resource.worker_type_label) if value
    ) or "No role assigned"
    context = " | ".join(
        value for value in (resource.organization_label, resource.department, resource.site) if value
    )
    return ResourceRecordViewModel(
        id=resource.id,
        title=resource.name,
        status_label=resource.active_label,
        subtitle=subtitle,
        supporting_text=f"Capacity modifier {resource.capacity_label}",
        meta_text=context,
        state=state,
    )


__all__ = ["to_resource_record_view_model"]
