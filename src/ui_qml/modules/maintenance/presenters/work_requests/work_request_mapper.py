from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.work_requests import (
    MaintenanceWorkRequestRecordViewModel,
)


def work_request_record(row) -> MaintenanceWorkRequestRecordViewModel:
    return MaintenanceWorkRequestRecordViewModel(
        id=row.id,
        title=row.work_request_code or row.title,
        status_label=row.status_label,
        subtitle=row.title,
        supporting_text=(
            f"{row.priority_label} | {row.asset_label} | {row.location_label}"
        ),
        meta_text=(
            f"Requested {row.requested_at or '-'} by {row.requested_by_name or '-'}"
        ),
        state={
            "workRequestId": row.id,
            "workRequestCode": row.work_request_code,
            "siteId": row.site_id,
            "siteLabel": row.site_label,
            "assetId": row.asset_id or "",
            "assetLabel": row.asset_label,
            "componentId": row.component_id or "",
            "systemId": row.system_id or "",
            "locationId": row.location_id or "",
            "locationLabel": row.location_label,
            "sourceType": row.source_type,
            "sourceId": row.source_id or "",
            "requestType": row.request_type,
            "title": row.title,
            "description": row.description,
            "priority": row.priority,
            "priorityLabel": row.priority_label,
            "status": row.status,
            "requestedAt": row.requested_at or "",
            "requestedByName": row.requested_by_name or "",
            "failureSymptomCode": row.failure_symptom_code,
            "safetyRiskLevel": row.safety_risk_level,
            "productionImpactLevel": row.production_impact_level,
            "notes": row.notes,
            "expectedVersion": row.version,
            "canPrimaryAction": True,
            "canSecondaryAction": True,
        },
    )
