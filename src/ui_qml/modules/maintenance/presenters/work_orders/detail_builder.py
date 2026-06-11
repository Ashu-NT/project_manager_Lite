from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.work_orders import (
    MaintenanceWorkOrderDetailFieldViewModel,
    MaintenanceWorkOrderDetailViewModel,
)

from .formatting import money_text, yes_no


def build_detail(row) -> MaintenanceWorkOrderDetailViewModel:
    if row is None:
        return MaintenanceWorkOrderDetailViewModel(
            title="No work order selected",
            empty_state=(
                "Select a work order to inspect its execution scope, planning status, "
                "and update actions."
            ),
        )
    return MaintenanceWorkOrderDetailViewModel(
        id=row.id,
        title=f"{row.work_order_code or '-'} - {row.title}",
        status_label=row.status_label,
        subtitle=f"{row.priority_label} | {row.site_label}",
        description=row.description or "No execution description provided.",
        fields=(
            MaintenanceWorkOrderDetailFieldViewModel(
                label="Type / Source",
                value=f"{row.work_order_type_label} | {row.source_type_label}",
                supporting_text=row.source_label,
            ),
            MaintenanceWorkOrderDetailFieldViewModel(
                label="Anchor",
                value=f"{row.asset_label} | {row.component_label}",
                supporting_text=f"{row.system_label} | {row.location_label}",
            ),
            MaintenanceWorkOrderDetailFieldViewModel(
                label="Assignment",
                value=row.assigned_employee_label or "-",
                supporting_text=f"Vendor: {row.vendor_party_label or '-'}",
            ),
            MaintenanceWorkOrderDetailFieldViewModel(
                label="Plan window",
                value=row.planned_start or "-",
                supporting_text=f"End: {row.planned_end or '-'}",
            ),
            MaintenanceWorkOrderDetailFieldViewModel(
                label="Execution window",
                value=row.actual_start or "-",
                supporting_text=f"End: {row.actual_end or '-'}",
            ),
            MaintenanceWorkOrderDetailFieldViewModel(
                label="Flags",
                value=(
                    f"Shutdown {yes_no(row.requires_shutdown)} | "
                    f"Permit {yes_no(row.permit_required)} | "
                    f"Approval {yes_no(row.approval_required)}"
                ),
                supporting_text=(
                    f"Preventive {yes_no(row.is_preventive)} | "
                    f"Emergency {yes_no(row.is_emergency)}"
                ),
            ),
            MaintenanceWorkOrderDetailFieldViewModel(
                label="Failure / Cost",
                value=f"{row.failure_code or '-'} | {row.root_cause_code or '-'}",
                supporting_text=(
                    f"Labor {money_text(row.labor_cost)} | "
                    f"Parts {money_text(row.parts_cost)} | "
                    f"Downtime {row.downtime_minutes if row.downtime_minutes is not None else '-'} min"
                ),
            ),
            MaintenanceWorkOrderDetailFieldViewModel(
                label="Notes",
                value=row.notes or "-",
            ),
            MaintenanceWorkOrderDetailFieldViewModel(
                label="Version",
                value=str(row.version),
            ),
        ),
        state={
            "workOrderId": row.id,
            "siteId": row.site_id,
            "workOrderCode": row.work_order_code,
            "workOrderType": row.work_order_type,
            "sourceType": row.source_type,
            "sourceId": row.source_id or "",
            "sourceLabel": row.source_label,
            "assetId": row.asset_id or "",
            "componentId": row.component_id or "",
            "systemId": row.system_id or "",
            "locationId": row.location_id or "",
            "title": row.title,
            "description": row.description,
            "priority": row.priority,
            "status": row.status,
            "assignedEmployeeId": row.assigned_employee_id or "",
            "vendorPartyId": row.vendor_party_id or "",
            "plannedStart": row.planned_start,
            "plannedEnd": row.planned_end,
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
