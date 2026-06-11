from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.work_requests import (
    MaintenanceWorkRequestDetailFieldViewModel,
    MaintenanceWorkRequestDetailViewModel,
)


def build_detail(row) -> MaintenanceWorkRequestDetailViewModel:
    if row is None:
        return MaintenanceWorkRequestDetailViewModel(
            title="No work request selected",
            empty_state=(
                "Select a work request to inspect its intake context, triage state, "
                "and update actions."
            ),
        )
    return MaintenanceWorkRequestDetailViewModel(
        id=row.id,
        title=f"{row.work_request_code or '-'} - {row.title}",
        status_label=row.status_label,
        subtitle=f"{row.priority_label} | {row.site_label}",
        description=row.description or "No request description provided.",
        fields=(
            MaintenanceWorkRequestDetailFieldViewModel(
                label="Source",
                value=f"{row.source_type_label} | {row.source_id or '-'}",
            ),
            MaintenanceWorkRequestDetailFieldViewModel(
                label="Request type",
                value=row.request_type or "-",
            ),
            MaintenanceWorkRequestDetailFieldViewModel(
                label="Anchor",
                value=f"{row.asset_label} | {row.component_label}",
                supporting_text=f"{row.system_label} | {row.location_label}",
            ),
            MaintenanceWorkRequestDetailFieldViewModel(
                label="Requested",
                value=row.requested_at or "-",
                supporting_text=f"By {row.requested_by_name or '-'}",
            ),
            MaintenanceWorkRequestDetailFieldViewModel(
                label="Triaged",
                value=row.triaged_at or "-",
                supporting_text=f"By {row.triaged_by_label or '-'}",
            ),
            MaintenanceWorkRequestDetailFieldViewModel(
                label="Failure / Risk",
                value=row.failure_symptom_code or "-",
                supporting_text=(
                    f"Safety {row.safety_risk_level or '-'} | "
                    f"Production {row.production_impact_level or '-'}"
                ),
            ),
            MaintenanceWorkRequestDetailFieldViewModel(
                label="Notes",
                value=row.notes or "-",
            ),
            MaintenanceWorkRequestDetailFieldViewModel(
                label="Version",
                value=str(row.version),
            ),
        ),
        state={
            "workRequestId": row.id,
            "workRequestCode": row.work_request_code,
            "siteId": row.site_id,
            "assetId": row.asset_id or "",
            "componentId": row.component_id or "",
            "systemId": row.system_id or "",
            "locationId": row.location_id or "",
            "sourceType": row.source_type,
            "sourceId": row.source_id or "",
            "requestType": row.request_type,
            "title": row.title,
            "description": row.description,
            "priority": row.priority,
            "status": row.status,
            "failureSymptomCode": row.failure_symptom_code,
            "safetyRiskLevel": row.safety_risk_level,
            "productionImpactLevel": row.production_impact_level,
            "notes": row.notes,
            "expectedVersion": row.version,
            "canPrimaryAction": True,
            "canSecondaryAction": True,
        },
    )
