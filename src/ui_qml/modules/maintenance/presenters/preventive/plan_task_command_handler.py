from __future__ import annotations

from src.core.modules.maintenance.api.desktop import (
    MaintenancePreventivePlanTaskCreateCommand,
    MaintenancePreventivePlanTaskUpdateCommand,
)

from .validation import (
    optional_bool,
    optional_int,
    optional_optional_bool,
    optional_text,
    require_int,
    require_text,
)


def create_plan_task(desktop_api, payload: dict) -> None:
    desktop_api.create_plan_task(
        MaintenancePreventivePlanTaskCreateCommand(
            plan_id=require_text(payload, "planId", "Choose a preventive plan first."),
            task_template_id=require_text(
                payload,
                "taskTemplateId",
                "Choose a task template before saving.",
            ),
            trigger_scope=optional_text(payload, "triggerScope") or "INHERIT_PLAN",
            trigger_mode_override=optional_text(payload, "triggerModeOverride"),
            calendar_frequency_unit_override=optional_text(
                payload,
                "calendarFrequencyUnitOverride",
            ),
            calendar_frequency_value_override=optional_int(
                payload,
                "calendarFrequencyValueOverride",
            ),
            sensor_id_override=optional_text(payload, "sensorIdOverride"),
            sensor_threshold_override=optional_text(payload, "sensorThresholdOverride"),
            sensor_direction_override=optional_text(payload, "sensorDirectionOverride"),
            sequence_no=optional_int(payload, "sequenceNo"),
            is_mandatory=optional_bool(payload, "isMandatory", True),
            default_assigned_team_id=optional_text(payload, "defaultAssignedTeamId"),
            estimated_minutes_override=optional_int(payload, "estimatedMinutesOverride"),
            notes=optional_text(payload, "notes") or "",
        )
    )


def update_plan_task(desktop_api, payload: dict) -> None:
    desktop_api.update_plan_task(
        MaintenancePreventivePlanTaskUpdateCommand(
            plan_task_id=require_text(
                payload,
                "planTaskId",
                "Plan task ID is required.",
            ),
            task_template_id=optional_text(payload, "taskTemplateId"),
            trigger_scope=optional_text(payload, "triggerScope"),
            trigger_mode_override=optional_text(payload, "triggerModeOverride"),
            calendar_frequency_unit_override=optional_text(
                payload,
                "calendarFrequencyUnitOverride",
            ),
            calendar_frequency_value_override=optional_int(
                payload,
                "calendarFrequencyValueOverride",
            ),
            sensor_id_override=optional_text(payload, "sensorIdOverride"),
            sensor_threshold_override=optional_text(payload, "sensorThresholdOverride"),
            sensor_direction_override=optional_text(payload, "sensorDirectionOverride"),
            sequence_no=optional_int(payload, "sequenceNo"),
            is_mandatory=optional_optional_bool(payload, "isMandatory"),
            default_assigned_team_id=optional_text(payload, "defaultAssignedTeamId"),
            estimated_minutes_override=optional_int(payload, "estimatedMinutesOverride"),
            notes=optional_text(payload, "notes"),
            expected_version=require_int(
                payload,
                "expectedVersion",
                "Expected version is required before saving.",
            ),
        )
    )
