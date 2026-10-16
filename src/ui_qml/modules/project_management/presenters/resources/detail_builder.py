from __future__ import annotations

from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_money,
)
from src.core.modules.project_management.api.desktop.resources.formatters.enum_formatter import (
    format_enum_label,
)
from src.core.modules.project_management.contracts.reads.resources.models import (
    ResourceInspectorFact,
    ResourceSummaryFact,
)
from src.core.modules.project_management.domain.enums import WorkerType
from src.core.platform.domain.finance.money import canonical_decimal_text
from src.ui_qml.modules.project_management.view_models.resources import (
    ResourceDetailFieldViewModel,
    ResourceDetailViewModel,
    ResourceInspectorViewModel,
)


def build_resource_state(resource: ResourceSummaryFact) -> dict[str, object]:
    return {
        "resourceId": resource.resource_id,
        "name": resource.name,
        "resourceCode": resource.code,
        "role": resource.role,
        "kind": resource.kind,
        "kindLabel": format_enum_label(resource.kind),
        "workerType": resource.worker_type,
        "workerTypeLabel": format_enum_label(resource.worker_type),
        "costType": resource.cost_type,
        "costTypeLabel": format_enum_label(resource.cost_type),
        "hourlyRate": canonical_decimal_text(resource.hourly_rate),
        "hourlyRateLabel": format_money(resource.hourly_rate, resource.currency_code),
        "currency": resource.currency_code or "",
        "capacityPercent": f"{resource.capacity_percent:.1f}",
        "capacityLabel": f"{resource.capacity_percent:.1f}%",
        "address": resource.address,
        "contact": resource.contact,
        "organizationId": resource.organization_id,
        "organization": resource.organization_label,
        "departmentId": resource.department_id or "",
        "department": resource.department_label,
        "siteId": resource.site_id or "",
        "site": resource.site_label,
        "employeeId": resource.employee_id or "",
        "employeeName": resource.employee_name,
        "employeeContext": " | ".join(
            value for value in (resource.department_label, resource.site_label) if value
        )
        or "-",
        "isActive": resource.is_active,
        "activeLabel": "Active" if resource.is_active else "Inactive",
        "version": resource.version,
        "canRead": resource.can_read,
        "canManage": resource.can_manage,
    }


def build_detail_view_model(resource: ResourceSummaryFact) -> ResourceDetailViewModel:
    state = build_resource_state(resource)
    subtitle = " | ".join(
        value
        for value in (
            resource.role,
            resource.organization_label,
            resource.department_label,
        )
        if value
    ) or format_enum_label(resource.worker_type)
    description = (
        "Employee-linked resource. Platform identity remains authoritative."
        if resource.worker_type == WorkerType.EMPLOYEE.value
        else "External PM resource available for scoped project planning."
    )
    return ResourceDetailViewModel(
        id=resource.resource_id,
        title=resource.name,
        status_label="Active" if resource.is_active else "Inactive",
        subtitle=subtitle,
        description=description,
        fields=(
            ResourceDetailFieldViewModel("Code", resource.code or "-"),
            ResourceDetailFieldViewModel(
                "Resource kind", format_enum_label(resource.kind)
            ),
            ResourceDetailFieldViewModel(
                "Worker type", format_enum_label(resource.worker_type)
            ),
            ResourceDetailFieldViewModel("Role", resource.role or "-"),
            ResourceDetailFieldViewModel(
                "Organization", resource.organization_label or "-"
            ),
            ResourceDetailFieldViewModel(
                "Department", resource.department_label or "-"
            ),
            ResourceDetailFieldViewModel("Site", resource.site_label or "-"),
            ResourceDetailFieldViewModel(
                "Capacity modifier", f"{resource.capacity_percent:.1f}%"
            ),
            ResourceDetailFieldViewModel("Version", str(resource.version)),
        ),
        state=state,
    )


def build_inspector_view_model(
    resource: ResourceInspectorFact,
) -> ResourceInspectorViewModel:
    state = {
        "resourceId": resource.resource_id,
        "version": resource.version,
        "canRead": resource.can_read,
        "canManage": resource.can_manage,
        "canDeactivate": resource.can_deactivate,
        "canReactivate": resource.can_reactivate,
    }
    return ResourceInspectorViewModel(
        id=resource.resource_id,
        title=resource.name,
        status_label="Active" if resource.is_active else "Inactive",
        fields=(
            ResourceDetailFieldViewModel("Code", resource.code or "-"),
            ResourceDetailFieldViewModel("Role", resource.role or "-"),
            ResourceDetailFieldViewModel(
                "Engagement", format_enum_label(resource.worker_type)
            ),
            ResourceDetailFieldViewModel(
                "Organization", resource.organization_label or "-"
            ),
            ResourceDetailFieldViewModel(
                "Department", resource.department_label or "-"
            ),
            ResourceDetailFieldViewModel("Site", resource.site_label or "-"),
            ResourceDetailFieldViewModel(
                "Capacity modifier", f"{resource.capacity_percent:.1f}%"
            ),
            ResourceDetailFieldViewModel(
                "Active projects", str(resource.project_count)
            ),
            ResourceDetailFieldViewModel("Assignments", str(resource.assignment_count)),
        ),
        state=state,
    )


__all__ = [
    "build_detail_view_model",
    "build_inspector_view_model",
    "build_resource_state",
]
