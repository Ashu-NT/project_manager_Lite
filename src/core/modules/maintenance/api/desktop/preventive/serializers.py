from __future__ import annotations

from decimal import Decimal

from src.core.modules.maintenance.api.desktop._support import (
    clean_id,
    clean_text,
    code_name_label,
    datetime_text,
    enum_value,
    format_active_label,
    format_enum_label,
    int_value,
)
from src.core.modules.maintenance.api.desktop.preventive.models import (
    MaintenancePreventiveForecastRowDescriptor,
    MaintenancePreventiveGenerationResultDescriptor,
    MaintenancePreventivePlanDesktopDto,
    MaintenancePreventivePlanTaskDesktopDto,
    MaintenancePreventiveQueueRowDescriptor,
    MaintenanceTaskStepTemplateDesktopDto,
    MaintenanceTaskTemplateDesktopDto,
)


def _decimal_text(value: Decimal | None) -> str:
    if value is None:
        return ""
    return format(value.normalize(), "f") if isinstance(value, Decimal) else str(value)


def _timestamp_label(value) -> str:
    text = datetime_text(value)
    return text or "-"


def _next_due_label(*, next_due_at, next_due_counter) -> str:
    if next_due_at is not None:
        return datetime_text(next_due_at)
    if next_due_counter is not None:
        return _decimal_text(next_due_counter)
    return "-"


def anchor_label(
    row,
    *,
    site_lookup: dict[str, str],
    asset_lookup: dict[str, str],
    component_lookup: dict[str, str],
    system_lookup: dict[str, str],
) -> str:
    asset_id = clean_id(getattr(row, "asset_id", None))
    component_id = clean_id(getattr(row, "component_id", None))
    system_id = clean_id(getattr(row, "system_id", None))
    if asset_id:
        return asset_lookup.get(asset_id, asset_id)
    if component_id:
        return component_lookup.get(component_id, component_id)
    if system_id:
        return system_lookup.get(system_id, system_id)
    return site_lookup.get(getattr(row, "site_id", ""), "-")


def trigger_summary(row, *, sensor_lookup: dict[str, str]) -> str:
    trigger_mode = enum_value(getattr(row, "trigger_mode", ""))
    if trigger_mode == "CALENDAR":
        unit = format_enum_label(enum_value(getattr(row, "calendar_frequency_unit", "")))
        value = int_value(getattr(row, "calendar_frequency_value", None))
        if value is None:
            return "Calendar"
        return f"Every {value} {unit.lower()}"
    if trigger_mode == "SENSOR":
        sensor_label = sensor_lookup.get(clean_id(getattr(row, "sensor_id", None)) or "", "-")
        threshold = _decimal_text(getattr(row, "sensor_threshold", None))
        direction = format_enum_label(enum_value(getattr(row, "sensor_direction", "")))
        return f"{sensor_label} | {direction} {threshold}".strip()
    if trigger_mode == "HYBRID":
        return "Calendar + Sensor"
    return format_enum_label(trigger_mode)


def plan_task_trigger_summary(row, *, sensor_lookup: dict[str, str]) -> str:
    trigger_scope = enum_value(getattr(row, "trigger_scope", ""))
    if trigger_scope == "INHERIT_PLAN":
        return "Uses plan trigger"
    trigger_mode = enum_value(getattr(row, "trigger_mode_override", ""))
    if trigger_mode == "CALENDAR":
        unit = format_enum_label(
            enum_value(getattr(row, "calendar_frequency_unit_override", ""))
        )
        value = int_value(getattr(row, "calendar_frequency_value_override", None))
        if value is None:
            return "Task calendar override"
        return f"Task calendar: every {value} {unit.lower()}"
    if trigger_mode == "SENSOR":
        sensor_label = sensor_lookup.get(
            clean_id(getattr(row, "sensor_id_override", None)) or "",
            "-",
        )
        threshold = _decimal_text(getattr(row, "sensor_threshold_override", None))
        direction = format_enum_label(
            enum_value(getattr(row, "sensor_direction_override", ""))
        )
        return f"Task sensor: {sensor_label} | {direction} {threshold}".strip()
    if trigger_mode == "HYBRID":
        return "Task hybrid override"
    return format_enum_label(trigger_mode)


def serialize_task_template(
    row,
    *,
    step_count: int,
) -> MaintenanceTaskTemplateDesktopDto:
    maintenance_type = clean_text(getattr(row, "maintenance_type", "")).upper()
    template_status = enum_value(getattr(row, "template_status", ""))
    return MaintenanceTaskTemplateDesktopDto(
        id=row.id,
        task_template_code=clean_text(getattr(row, "task_template_code", "")),
        name=clean_text(getattr(row, "name", "")),
        description=clean_text(getattr(row, "description", "")),
        maintenance_type=maintenance_type,
        maintenance_type_label=format_enum_label(maintenance_type),
        revision_no=int(getattr(row, "revision_no", 0) or 0),
        template_status=template_status,
        template_status_label=format_enum_label(template_status),
        estimated_minutes=int_value(getattr(row, "estimated_minutes", None)),
        required_skill=clean_text(getattr(row, "required_skill", "")),
        requires_shutdown=bool(getattr(row, "requires_shutdown", False)),
        requires_permit=bool(getattr(row, "requires_permit", False)),
        is_active=bool(getattr(row, "is_active", True)),
        active_label=format_active_label(getattr(row, "is_active", True)),
        notes=clean_text(getattr(row, "notes", "")),
        created_at=datetime_text(getattr(row, "created_at", None)),
        updated_at=datetime_text(getattr(row, "updated_at", None)),
        version=int(getattr(row, "version", 0) or 0),
        step_count=step_count,
    )


def serialize_task_step_template(row) -> MaintenanceTaskStepTemplateDesktopDto:
    hint_level = clean_text(getattr(row, "hint_level", "")).upper()
    return MaintenanceTaskStepTemplateDesktopDto(
        id=row.id,
        task_template_id=row.task_template_id,
        step_number=int(getattr(row, "step_number", 0) or 0),
        sort_order=int(getattr(row, "sort_order", 0) or 0),
        instruction=clean_text(getattr(row, "instruction", "")),
        expected_result=clean_text(getattr(row, "expected_result", "")),
        hint_level=hint_level,
        hint_level_label=format_enum_label(hint_level),
        hint_text=clean_text(getattr(row, "hint_text", "")),
        requires_confirmation=bool(getattr(row, "requires_confirmation", False)),
        requires_measurement=bool(getattr(row, "requires_measurement", False)),
        requires_photo=bool(getattr(row, "requires_photo", False)),
        measurement_unit=clean_text(getattr(row, "measurement_unit", "")),
        is_active=bool(getattr(row, "is_active", True)),
        active_label=format_active_label(getattr(row, "is_active", True)),
        notes=clean_text(getattr(row, "notes", "")),
        created_at=datetime_text(getattr(row, "created_at", None)),
        updated_at=datetime_text(getattr(row, "updated_at", None)),
        version=int(getattr(row, "version", 0) or 0),
    )


def serialize_preventive_plan(
    row,
    *,
    site_lookup: dict[str, str],
    asset_lookup: dict[str, str],
    component_lookup: dict[str, str],
    system_lookup: dict[str, str],
    sensor_lookup: dict[str, str],
    plan_task_count: int,
) -> MaintenancePreventivePlanDesktopDto:
    status = enum_value(getattr(row, "status", ""))
    plan_type = enum_value(getattr(row, "plan_type", ""))
    priority = enum_value(getattr(row, "priority", ""))
    trigger_mode = enum_value(getattr(row, "trigger_mode", ""))
    schedule_policy = enum_value(getattr(row, "schedule_policy", ""))
    calendar_frequency_unit = enum_value(getattr(row, "calendar_frequency_unit", ""))
    generation_lead_unit = enum_value(getattr(row, "generation_lead_unit", ""))
    sensor_direction = enum_value(getattr(row, "sensor_direction", ""))
    asset_id = clean_id(getattr(row, "asset_id", None))
    component_id = clean_id(getattr(row, "component_id", None))
    system_id = clean_id(getattr(row, "system_id", None))
    sensor_id = clean_id(getattr(row, "sensor_id", None))
    return MaintenancePreventivePlanDesktopDto(
        id=row.id,
        site_id=row.site_id,
        site_label=site_lookup.get(row.site_id, "-"),
        plan_code=clean_text(getattr(row, "plan_code", "")),
        name=clean_text(getattr(row, "name", "")),
        anchor_label=anchor_label(
            row,
            site_lookup=site_lookup,
            asset_lookup=asset_lookup,
            component_lookup=component_lookup,
            system_lookup=system_lookup,
        ),
        asset_id=asset_id,
        asset_label=asset_lookup.get(asset_id or "", "-"),
        component_id=component_id,
        component_label=component_lookup.get(component_id or "", "-"),
        system_id=system_id,
        system_label=system_lookup.get(system_id or "", "-"),
        description=clean_text(getattr(row, "description", "")),
        status=status,
        status_label=format_enum_label(status),
        plan_type=plan_type,
        plan_type_label=format_enum_label(plan_type),
        priority=priority,
        priority_label=format_enum_label(priority),
        trigger_mode=trigger_mode,
        trigger_mode_label=format_enum_label(trigger_mode),
        trigger_summary=trigger_summary(row, sensor_lookup=sensor_lookup),
        schedule_policy=schedule_policy,
        schedule_policy_label=format_enum_label(schedule_policy),
        calendar_frequency_unit=calendar_frequency_unit,
        calendar_frequency_unit_label=format_enum_label(calendar_frequency_unit),
        calendar_frequency_value=int_value(
            getattr(row, "calendar_frequency_value", None)
        ),
        generation_horizon_count=int(
            getattr(row, "generation_horizon_count", 0) or 0
        ),
        generation_lead_value=int(
            getattr(row, "generation_lead_value", 0) or 0
        ),
        generation_lead_unit=generation_lead_unit,
        generation_lead_unit_label=format_enum_label(generation_lead_unit),
        sensor_id=sensor_id,
        sensor_label=sensor_lookup.get(sensor_id or "", "-"),
        sensor_threshold=_decimal_text(getattr(row, "sensor_threshold", None)),
        sensor_direction=sensor_direction,
        sensor_direction_label=format_enum_label(sensor_direction),
        sensor_reset_rule=clean_text(getattr(row, "sensor_reset_rule", "")),
        last_generated_at=datetime_text(getattr(row, "last_generated_at", None)),
        last_completed_at=datetime_text(getattr(row, "last_completed_at", None)),
        next_due_at=datetime_text(getattr(row, "next_due_at", None)),
        next_due_label=_next_due_label(
            next_due_at=getattr(row, "next_due_at", None),
            next_due_counter=getattr(row, "next_due_counter", None),
        ),
        next_due_counter=_decimal_text(getattr(row, "next_due_counter", None)),
        requires_shutdown=bool(getattr(row, "requires_shutdown", False)),
        approval_required=bool(getattr(row, "approval_required", False)),
        auto_generate_work_order=bool(getattr(row, "auto_generate_work_order", False)),
        is_active=bool(getattr(row, "is_active", True)),
        active_label=format_active_label(getattr(row, "is_active", True)),
        notes=clean_text(getattr(row, "notes", "")),
        created_at=datetime_text(getattr(row, "created_at", None)),
        updated_at=datetime_text(getattr(row, "updated_at", None)),
        version=int(getattr(row, "version", 0) or 0),
        plan_task_count=plan_task_count,
    )


def serialize_preventive_plan_task(
    row,
    *,
    task_template_lookup: dict[str, str],
    sensor_lookup: dict[str, str],
) -> MaintenancePreventivePlanTaskDesktopDto:
    trigger_scope = enum_value(getattr(row, "trigger_scope", ""))
    trigger_mode_override = enum_value(getattr(row, "trigger_mode_override", ""))
    sensor_id_override = clean_id(getattr(row, "sensor_id_override", None))
    return MaintenancePreventivePlanTaskDesktopDto(
        id=row.id,
        plan_id=row.plan_id,
        task_template_id=row.task_template_id,
        task_template_label=task_template_lookup.get(row.task_template_id, "-"),
        trigger_scope=trigger_scope,
        trigger_scope_label=format_enum_label(trigger_scope),
        trigger_mode_override=trigger_mode_override,
        trigger_mode_override_label=format_enum_label(trigger_mode_override),
        trigger_rule_summary=plan_task_trigger_summary(
            row,
            sensor_lookup=sensor_lookup,
        ),
        sensor_id_override=sensor_id_override,
        sensor_label_override=sensor_lookup.get(sensor_id_override or "", "-"),
        sequence_no=int(getattr(row, "sequence_no", 0) or 0),
        is_mandatory=bool(getattr(row, "is_mandatory", False)),
        default_assigned_team_id=clean_id(
            getattr(row, "default_assigned_team_id", None)
        ),
        estimated_minutes_override=int_value(
            getattr(row, "estimated_minutes_override", None)
        ),
        last_generated_at=datetime_text(getattr(row, "last_generated_at", None)),
        next_due_at=datetime_text(getattr(row, "next_due_at", None)),
        next_due_label=_next_due_label(
            next_due_at=getattr(row, "next_due_at", None),
            next_due_counter=getattr(row, "next_due_counter", None),
        ),
        next_due_counter=_decimal_text(getattr(row, "next_due_counter", None)),
        notes=clean_text(getattr(row, "notes", "")),
        version=int(getattr(row, "version", 0) or 0),
    )


def serialize_queue_row(
    plan,
    candidate,
    *,
    site_lookup: dict[str, str],
    asset_lookup: dict[str, str],
    component_lookup: dict[str, str],
    system_lookup: dict[str, str],
    sensor_lookup: dict[str, str],
) -> MaintenancePreventiveQueueRowDescriptor:
    target = clean_text(getattr(candidate, "generation_target", "")).upper()
    due_state = clean_text(getattr(candidate, "due_state", "")).upper()
    next_due_label = _next_due_label(
        next_due_at=getattr(plan, "next_due_at", None),
        next_due_counter=getattr(plan, "next_due_counter", None),
    )
    return MaintenancePreventiveQueueRowDescriptor(
        plan_id=plan.id,
        plan_code=clean_text(getattr(plan, "plan_code", "")),
        plan_label=code_name_label(
            getattr(plan, "plan_code", ""),
            getattr(plan, "name", ""),
        ),
        anchor_label=anchor_label(
            plan,
            site_lookup=site_lookup,
            asset_lookup=asset_lookup,
            component_lookup=component_lookup,
            system_lookup=system_lookup,
        ),
        plan_status=enum_value(getattr(plan, "status", "")),
        plan_status_label=format_enum_label(enum_value(getattr(plan, "status", ""))),
        due_state=due_state,
        due_state_label=format_enum_label(due_state),
        due_reason=clean_text(getattr(candidate, "due_reason", "")),
        generation_target=target,
        generation_target_label=format_enum_label(target),
        trigger_label=trigger_summary(plan, sensor_lookup=sensor_lookup),
        next_due_label=next_due_label,
        is_due_soon=due_state == "DUE_SOON",
        selected_plan_task_ids=tuple(getattr(candidate, "selected_plan_task_ids", ()) or ()),
        blocked_plan_task_ids=tuple(getattr(candidate, "blocked_plan_task_ids", ()) or ()),
        version=int(getattr(plan, "version", 0) or 0),
    )


def serialize_forecast_row(row) -> MaintenancePreventiveForecastRowDescriptor:
    instance_status = clean_text(getattr(row, "instance_status", "")).upper()
    planner_state = clean_text(getattr(row, "planner_state", "")).upper()
    return MaintenancePreventiveForecastRowDescriptor(
        instance_id=clean_text(getattr(row, "instance_id", "")),
        due_at_label=_timestamp_label(getattr(row, "due_at", None)),
        generation_window_opens_at_label=_timestamp_label(
            getattr(row, "generation_window_opens_at", None)
        ),
        instance_status=instance_status,
        instance_status_label=format_enum_label(instance_status),
        planner_state=planner_state,
        planner_state_label=format_enum_label(planner_state),
        generated_work_request_id=clean_id(
            getattr(row, "generated_work_request_id", None)
        ),
        generated_work_order_id=clean_id(
            getattr(row, "generated_work_order_id", None)
        ),
        completed_at_label=_timestamp_label(getattr(row, "completed_at", None)),
    )


def serialize_generation_result(
    row,
) -> MaintenancePreventiveGenerationResultDescriptor:
    target = clean_text(getattr(row, "generation_target", "")).upper()
    return MaintenancePreventiveGenerationResultDescriptor(
        plan_id=clean_text(getattr(row, "plan_id", "")),
        plan_code=clean_text(getattr(row, "plan_code", "")),
        generation_target=target,
        generation_target_label=format_enum_label(target),
        generated_work_request_id=clean_id(
            getattr(row, "generated_work_request_id", None)
        ),
        generated_work_order_id=clean_id(
            getattr(row, "generated_work_order_id", None)
        ),
        generated_task_count=len(tuple(getattr(row, "generated_task_ids", ()) or ())),
        generated_step_count=len(tuple(getattr(row, "generated_step_ids", ()) or ())),
        skipped_reason=clean_text(getattr(row, "skipped_reason", "")),
    )


__all__ = [
    "anchor_label",
    "serialize_forecast_row",
    "serialize_generation_result",
    "serialize_preventive_plan",
    "serialize_preventive_plan_task",
    "serialize_queue_row",
    "serialize_task_step_template",
    "serialize_task_template",
    "trigger_summary",
]
