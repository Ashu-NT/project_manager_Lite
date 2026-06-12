from __future__ import annotations

from src.core.modules.maintenance.api.desktop import (
    MaintenanceWorkRequestCreateCommand,
    MaintenanceWorkRequestUpdateCommand,
)

from .validation import optional_text, require_int, require_text


def create_work_request(desktop_api, payload: dict) -> None:
    desktop_api.create_work_request(
        MaintenanceWorkRequestCreateCommand(
            site_id=require_text(payload, "siteId", "Choose a site before saving."),
            work_request_code=optional_text(payload, "workRequestCode") or "",
            source_type=require_text(
                payload,
                "sourceType",
                "Choose a source type before saving.",
            ),
            source_id=optional_text(payload, "sourceId"),
            request_type=require_text(
                payload,
                "requestType",
                "Request type is required.",
            ),
            asset_id=optional_text(payload, "assetId"),
            component_id=optional_text(payload, "componentId"),
            system_id=optional_text(payload, "systemId"),
            location_id=optional_text(payload, "locationId"),
            title=require_text(payload, "title", "Title is required."),
            description=optional_text(payload, "description") or "",
            priority=require_text(payload, "priority", "Choose a priority."),
            failure_symptom_code=optional_text(payload, "failureSymptomCode") or "",
            safety_risk_level=optional_text(payload, "safetyRiskLevel") or "",
            production_impact_level=optional_text(payload, "productionImpactLevel") or "",
            notes=optional_text(payload, "notes") or "",
        )
    )


def update_work_request(desktop_api, payload: dict) -> None:
    desktop_api.update_work_request(
        MaintenanceWorkRequestUpdateCommand(
            work_request_id=require_text(
                payload,
                "workRequestId",
                "Work request ID is required before saving.",
            ),
            work_request_code=optional_text(payload, "workRequestCode"),
            request_type=optional_text(payload, "requestType"),
            asset_id=optional_text(payload, "assetId"),
            component_id=optional_text(payload, "componentId"),
            system_id=optional_text(payload, "systemId"),
            location_id=optional_text(payload, "locationId"),
            title=optional_text(payload, "title"),
            description=optional_text(payload, "description"),
            priority=optional_text(payload, "priority"),
            status=optional_text(payload, "status"),
            failure_symptom_code=optional_text(payload, "failureSymptomCode"),
            safety_risk_level=optional_text(payload, "safetyRiskLevel"),
            production_impact_level=optional_text(payload, "productionImpactLevel"),
            notes=optional_text(payload, "notes"),
            expected_version=require_int(
                payload,
                "expectedVersion",
                "Expected version is required before saving.",
            ),
        )
    )
