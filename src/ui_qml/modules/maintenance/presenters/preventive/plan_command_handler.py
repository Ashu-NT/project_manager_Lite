from __future__ import annotations

from src.core.modules.maintenance.api.desktop import (
    MaintenancePreventivePlanCreateCommand,
    MaintenancePreventivePlanUpdateCommand,
)

from .validation import (
    optional_bool,
    optional_int,
    optional_optional_bool,
    optional_text,
    require_int,
    require_text,
)


def create_plan(desktop_api, payload: dict) -> None:
    desktop_api.create_preventive_plan(
        MaintenancePreventivePlanCreateCommand(
            site_id=require_text(payload, "siteId", "Choose a site before saving."),
            plan_code=require_text(payload, "planCode", "Plan code is required."),
            name=require_text(payload, "name", "Plan name is required."),
            asset_id=optional_text(payload, "assetId"),
            component_id=optional_text(payload, "componentId"),
            system_id=optional_text(payload, "systemId"),
            description=optional_text(payload, "description") or "",
            status=optional_text(payload, "status") or "ACTIVE",
            plan_type=optional_text(payload, "planType") or "PREVENTIVE",
            priority=optional_text(payload, "priority") or "MEDIUM",
            trigger_mode=optional_text(payload, "triggerMode") or "CALENDAR",
            schedule_policy=optional_text(payload, "schedulePolicy") or "FIXED",
            calendar_frequency_unit=optional_text(payload, "calendarFrequencyUnit"),
            calendar_frequency_value=optional_int(payload, "calendarFrequencyValue"),
            generation_horizon_count=optional_int(payload, "generationHorizonCount"),
            generation_lead_value=optional_int(payload, "generationLeadValue"),
            generation_lead_unit=optional_text(payload, "generationLeadUnit") or "DAYS",
            sensor_id=optional_text(payload, "sensorId"),
            sensor_threshold=optional_text(payload, "sensorThreshold"),
            sensor_direction=optional_text(payload, "sensorDirection"),
            sensor_reset_rule=optional_text(payload, "sensorResetRule") or "",
            requires_shutdown=optional_bool(payload, "requiresShutdown", False),
            approval_required=optional_bool(payload, "approvalRequired", False),
            auto_generate_work_order=optional_bool(payload, "autoGenerateWorkOrder", False),
            is_active=optional_bool(payload, "isActive", True),
            notes=optional_text(payload, "notes") or "",
        )
    )


def update_plan(desktop_api, payload: dict) -> None:
    desktop_api.update_preventive_plan(
        MaintenancePreventivePlanUpdateCommand(
            plan_id=require_text(payload, "planId", "Plan ID is required."),
            site_id=optional_text(payload, "siteId"),
            plan_code=optional_text(payload, "planCode"),
            name=optional_text(payload, "name"),
            asset_id=optional_text(payload, "assetId"),
            component_id=optional_text(payload, "componentId"),
            system_id=optional_text(payload, "systemId"),
            description=optional_text(payload, "description"),
            status=optional_text(payload, "status"),
            plan_type=optional_text(payload, "planType"),
            priority=optional_text(payload, "priority"),
            trigger_mode=optional_text(payload, "triggerMode"),
            schedule_policy=optional_text(payload, "schedulePolicy"),
            calendar_frequency_unit=optional_text(payload, "calendarFrequencyUnit"),
            calendar_frequency_value=optional_int(payload, "calendarFrequencyValue"),
            generation_horizon_count=optional_int(payload, "generationHorizonCount"),
            generation_lead_value=optional_int(payload, "generationLeadValue"),
            generation_lead_unit=optional_text(payload, "generationLeadUnit"),
            sensor_id=optional_text(payload, "sensorId"),
            sensor_threshold=optional_text(payload, "sensorThreshold"),
            sensor_direction=optional_text(payload, "sensorDirection"),
            sensor_reset_rule=optional_text(payload, "sensorResetRule"),
            requires_shutdown=optional_optional_bool(payload, "requiresShutdown"),
            approval_required=optional_optional_bool(payload, "approvalRequired"),
            auto_generate_work_order=optional_optional_bool(payload, "autoGenerateWorkOrder"),
            is_active=optional_optional_bool(payload, "isActive"),
            notes=optional_text(payload, "notes"),
            expected_version=require_int(
                payload,
                "expectedVersion",
                "Expected version is required before saving.",
            ),
        )
    )


def toggle_plan_active(
    desktop_api,
    *,
    plan_id: str,
    is_active: bool,
    expected_version: int,
) -> None:
    desktop_api.update_preventive_plan(
        MaintenancePreventivePlanUpdateCommand(
            plan_id=plan_id,
            is_active=is_active,
            expected_version=expected_version,
        )
    )


def regenerate_plan_schedule(desktop_api, *, plan_id: str) -> None:
    desktop_api.regenerate_plan_schedule(plan_id=plan_id)
