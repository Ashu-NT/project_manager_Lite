from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    ProjectManagementResourcesDesktopApi,
)
from src.core.modules.project_management.domain.enums import WorkerType
from src.ui_qml.modules.project_management.view_models.resources import (
    ResourceDetailFieldViewModel,
    ResourceDetailViewModel,
)

def build_resource_state(resource: Any) -> dict[str, object]:
    return {
        "resourceId": resource.id,
        "name": resource.name,
        "resourceCode": getattr(resource, "code", "") or "",
        "role": resource.role or "",
        "workerType": resource.worker_type,
        "workerTypeLabel": resource.worker_type_label,
        "costType": resource.cost_type,
        "costTypeLabel": resource.cost_type_label,
        "hourlyRate": f"{float(resource.hourly_rate or 0.0):.2f}",
        "hourlyRateLabel": resource.hourly_rate_label,
        "currency": resource.currency_code or "",
        "capacityPercent": f"{float(resource.capacity_percent or 0.0):.1f}",
        "capacityLabel": resource.capacity_label,
        "address": resource.address or "",
        "contact": resource.contact or "",
        "employeeId": resource.employee_id or "",
        "employeeContext": resource.employee_context or "-",
        "department": getattr(resource, "department", "") or "",
        "site": getattr(resource, "site", "") or "",
        "isActive": resource.is_active,
        "activeLabel": resource.active_label,
        "version": resource.version,
    }

def build_detail_view_model(
    desktop_api: ProjectManagementResourcesDesktopApi,
    resource: Any,
) -> ResourceDetailViewModel:
    if resource is None:
        return ResourceDetailViewModel(
            title="No resource selected",
            empty_state="Select a resource from the catalog to review details or edit its setup.",
        )
    state = build_resource_state(resource)
    try:
        assignments = desktop_api.list_resource_assignments(resource.id)
        activity_items = [
            {
                "title": f"Assigned to {a.task_name}",
                "metaText": a.project_name or "",
                "statusLabel": a.allocation_label,
            }
            for a in assignments
        ]
    except Exception:
        activity_items = []
    state = {**state, "activityItems": activity_items}
    subtitle_parts = [state["role"], state["employeeContext"]]
    subtitle_values = [part for part in subtitle_parts if part and part != "-"]
    if not subtitle_values:
        subtitle_values = [state["workerTypeLabel"]]
    description = (
        "Employee-linked resource ready for cross-workspace staffing."
        if state["workerType"] == WorkerType.EMPLOYEE.value
        else "External resource record ready for project assignment and cost planning."
    )
    return ResourceDetailViewModel(
        id=resource.id,
        title=resource.name,
        status_label=resource.active_label,
        subtitle=" | ".join(subtitle_values),
        description=description,
        fields=(
            ResourceDetailFieldViewModel(
                label="Worker type",
                value=state["workerTypeLabel"],
                supporting_text=state["employeeContext"],
            ),
            ResourceDetailFieldViewModel(
                label="Department",
                value=state["department"] or "No department assigned",
            ),
            ResourceDetailFieldViewModel(
                label="Site",
                value=state["site"] or "No site assigned",
            ),
            ResourceDetailFieldViewModel(
                label="Category",
                value=state["costTypeLabel"],
            ),
            ResourceDetailFieldViewModel(
                label="Hourly rate",
                value=state["hourlyRateLabel"],
                supporting_text=state["currency"] or "Uses the PM default currency when left blank.",
            ),
            ResourceDetailFieldViewModel(
                label="Capacity",
                value=state["capacityLabel"],
            ),
            ResourceDetailFieldViewModel(
                label="Contact",
                value=state["contact"] or "No contact recorded",
            ),
            ResourceDetailFieldViewModel(
                label="Address",
                value=state["address"] or "No address recorded",
            ),
            ResourceDetailFieldViewModel(
                label="Version",
                value=str(state["version"]),
            ),
        ),
        state=state,
    )
