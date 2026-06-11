from __future__ import annotations

from src.core.modules.maintenance.api.desktop import (
    MaintenanceWorkOrderCreateCommand,
    MaintenanceWorkOrderUpdateCommand,
)

from .validation import bool_value, optional_text, require_int, require_text


def create_work_order(desktop_api, payload: dict) -> None:
    source_type = require_text(payload, "sourceType", "Choose a source type before saving.")
    source_id = optional_text(payload, "sourceId")
    title = optional_text(payload, "title") or ""
    if source_type == "WORK_REQUEST" and not source_id:
        raise ValueError(
            "Choose a source work request before saving a converted work order."
        )
    if source_type != "WORK_REQUEST" and not title:
        raise ValueError("Title is required.")
    desktop_api.create_work_order(
        MaintenanceWorkOrderCreateCommand(
            site_id=require_text(payload, "siteId", "Choose a site before saving."),
            work_order_code=require_text(
                payload,
                "workOrderCode",
                "Work order code is required.",
            ),
            work_order_type=require_text(
                payload,
                "workOrderType",
                "Choose a work-order type before saving.",
            ),
            source_type=source_type,
            source_id=source_id,
            asset_id=optional_text(payload, "assetId"),
            component_id=optional_text(payload, "componentId"),
            system_id=optional_text(payload, "systemId"),
            location_id=optional_text(payload, "locationId"),
            title=title,
            description=optional_text(payload, "description") or "",
            priority=require_text(payload, "priority", "Choose a priority."),
            vendor_party_id=optional_text(payload, "vendorPartyId"),
            requires_shutdown=bool_value(payload, "requiresShutdown"),
            permit_required=bool_value(payload, "permitRequired"),
            approval_required=bool_value(payload, "approvalRequired"),
            is_preventive=bool_value(payload, "isPreventive"),
            is_emergency=bool_value(payload, "isEmergency"),
            notes=optional_text(payload, "notes") or "",
        )
    )


def update_work_order(desktop_api, payload: dict) -> None:
    title = require_text(payload, "title", "Title is required.")
    desktop_api.update_work_order(
        MaintenanceWorkOrderUpdateCommand(
            work_order_id=require_text(
                payload,
                "workOrderId",
                "Work order ID is required before saving.",
            ),
            work_order_code=require_text(
                payload,
                "workOrderCode",
                "Work order code is required.",
            ),
            work_order_type=require_text(
                payload,
                "workOrderType",
                "Choose a work-order type before saving.",
            ),
            source_id=optional_text(payload, "sourceId"),
            asset_id=optional_text(payload, "assetId"),
            component_id=optional_text(payload, "componentId"),
            system_id=optional_text(payload, "systemId"),
            location_id=optional_text(payload, "locationId"),
            title=title,
            description=optional_text(payload, "description") or "",
            priority=require_text(payload, "priority", "Choose a priority."),
            vendor_party_id=optional_text(payload, "vendorPartyId"),
            requires_shutdown=bool_value(payload, "requiresShutdown"),
            permit_required=bool_value(payload, "permitRequired"),
            approval_required=bool_value(payload, "approvalRequired"),
            is_preventive=bool_value(payload, "isPreventive"),
            is_emergency=bool_value(payload, "isEmergency"),
            notes=optional_text(payload, "notes") or "",
            expected_version=require_int(
                payload,
                "expectedVersion",
                "Expected version is required before saving.",
            ),
        )
    )
