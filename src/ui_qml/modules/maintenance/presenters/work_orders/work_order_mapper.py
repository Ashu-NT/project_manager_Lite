from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.work_orders import (
    MaintenanceWorkOrderRecordViewModel,
)


def work_order_record(row) -> MaintenanceWorkOrderRecordViewModel:
    plan_window = " | ".join(
        value
        for value in (row.planned_start or "", row.planned_end or "")
        if value
    )
    return MaintenanceWorkOrderRecordViewModel(
        id=row.id,
        title=row.work_order_code or row.title,
        status_label=row.status_label,
        subtitle=row.title,
        supporting_text=(
            f"{row.priority_label} | {row.work_order_type_label} | {row.asset_label}"
        ),
        meta_text=plan_window or f"Assigned: {row.assigned_employee_label}",
        state={
            "workOrderId": row.id,
            "siteId": row.site_id,
            "siteLabel": row.site_label,
            "workOrderCode": row.work_order_code,
            "workOrderType": row.work_order_type,
            "workOrderTypeLabel": row.work_order_type_label,
            "sourceType": row.source_type,
            "sourceId": row.source_id or "",
            "sourceLabel": row.source_label,
            "assetId": row.asset_id or "",
            "assetLabel": row.asset_label,
            "componentId": row.component_id or "",
            "systemId": row.system_id or "",
            "locationId": row.location_id or "",
            "title": row.title,
            "description": row.description,
            "priority": row.priority,
            "priorityLabel": row.priority_label,
            "status": row.status,
            "assignedEmployeeId": row.assigned_employee_id or "",
            "assignedEmployeeLabel": row.assigned_employee_label,
            "vendorPartyId": row.vendor_party_id or "",
            "plannedStart": row.planned_start or "",
            "plannedEnd": row.planned_end or "",
            "requiresShutdown": row.requires_shutdown,
            "permitRequired": row.permit_required,
            "approvalRequired": row.approval_required,
            "isPreventive": row.is_preventive,
            "isEmergency": row.is_emergency,
            "failureCode": row.failure_code,
            "rootCauseCode": row.root_cause_code,
            "downtimeMinutes": row.downtime_minutes if row.downtime_minutes is not None else "",
            "partsCost": row.parts_cost if row.parts_cost is not None else "",
            "laborCost": row.labor_cost if row.labor_cost is not None else "",
            "notes": row.notes,
            "expectedVersion": row.version,
            "canPrimaryAction": True,
            "canSecondaryAction": True,
        },
    )
