from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.core.modules.maintenance.api.desktop._support import (
    clean_text,
    code_name_label,
    enum_value,
    format_enum_label,
)
from src.core.modules.maintenance.api.desktop.planner.models import (
    MaintenancePlannerMaterialRiskRowDescriptor,
    MaintenancePlannerPreventiveRowDescriptor,
    MaintenancePlannerRecurringRowDescriptor,
    MaintenancePlannerRequestRowDescriptor,
    MaintenancePlannerWorkOrderRowDescriptor,
)

_PREVENTIVE_DUE_SOON_WINDOW = timedelta(days=30)


def format_timestamp_label(value: datetime | None) -> str:
    if value is None:
        return "-"
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat(sep=" ", timespec="minutes")


def planner_anchor_label(
    *,
    asset_id: str | None,
    system_id: str | None,
    location_id: str | None,
    site_id: str,
    site_lookup: dict[str, str],
    asset_lookup: dict[str, str],
    system_lookup: dict[str, str],
) -> str:
    if asset_id:
        return asset_lookup.get(asset_id, asset_id)
    if system_id:
        return system_lookup.get(system_id, system_id)
    if location_id:
        return location_id
    return site_lookup.get(site_id, site_id)


def serialize_request_row(
    row,
    *,
    site_lookup: dict[str, str],
    asset_lookup: dict[str, str],
    system_lookup: dict[str, str],
) -> MaintenancePlannerRequestRowDescriptor:
    status = enum_value(getattr(row, "status", ""))
    priority = enum_value(getattr(row, "priority", ""))
    return MaintenancePlannerRequestRowDescriptor(
        id=row.id,
        request_label=code_name_label(
            getattr(row, "work_request_code", ""),
            getattr(row, "title", ""),
        ),
        anchor_label=planner_anchor_label(
            asset_id=getattr(row, "asset_id", None),
            system_id=getattr(row, "system_id", None),
            location_id=getattr(row, "location_id", None),
            site_id=getattr(row, "site_id", ""),
            site_lookup=site_lookup,
            asset_lookup=asset_lookup,
            system_lookup=system_lookup,
        ),
        status=status,
        status_label=format_enum_label(status),
        priority=priority,
        priority_label=format_enum_label(priority),
    )


def serialize_work_order_row(row) -> MaintenancePlannerWorkOrderRowDescriptor:
    work_order_type = enum_value(getattr(row, "work_order_type", ""))
    status = enum_value(getattr(row, "status", ""))
    priority = enum_value(getattr(row, "priority", ""))
    return MaintenancePlannerWorkOrderRowDescriptor(
        id=row.id,
        work_order_label=code_name_label(
            getattr(row, "work_order_code", ""),
            getattr(row, "title", ""),
        ),
        work_order_type=work_order_type,
        work_order_type_label=format_enum_label(work_order_type),
        status=status,
        status_label=format_enum_label(status),
        priority=priority,
        priority_label=format_enum_label(priority),
        plan_window_label=format_window_label(
            getattr(row, "planned_start", None),
            getattr(row, "planned_end", None),
        ),
    )


def serialize_material_risk_row(
    row,
    *,
    work_order_label: str,
) -> MaintenancePlannerMaterialRiskRowDescriptor:
    procurement_status = enum_value(getattr(row, "procurement_status", ""))
    required_qty = getattr(row, "required_qty", None)
    issued_qty = getattr(row, "issued_qty", None)
    required_uom = clean_text(getattr(row, "required_uom", ""), default="-")
    return MaintenancePlannerMaterialRiskRowDescriptor(
        id=row.id,
        work_order_id=getattr(row, "work_order_id", ""),
        work_order_label=work_order_label,
        material_label=clean_text(getattr(row, "description", ""), default="-"),
        procurement_status=procurement_status,
        procurement_status_label=format_enum_label(procurement_status),
        quantity_label=f"{issued_qty}/{required_qty} {required_uom}",
        storeroom_label=clean_text(getattr(row, "preferred_storeroom_id", ""), default="-"),
    )


def serialize_preventive_row(
    plan,
    *,
    candidate,
    site_lookup: dict[str, str],
    asset_lookup: dict[str, str],
    system_lookup: dict[str, str],
) -> MaintenancePlannerPreventiveRowDescriptor:
    due_state = "NOT_DUE"
    due_reason = "Preventive plan is not currently due."
    generation_target = "WORK_ORDER" if bool(getattr(plan, "auto_generate_work_order", False)) else "WORK_REQUEST"
    if not bool(getattr(plan, "is_active", True)) or enum_value(getattr(plan, "status", "")) != "ACTIVE":
        due_state = "INACTIVE"
        due_reason = "Preventive plan is not active for due generation."
    elif candidate is not None:
        due_state = clean_text(getattr(candidate, "due_state", "NOT_DUE"), default="NOT_DUE")
        due_reason = clean_text(
            getattr(candidate, "due_reason", ""),
            default="Preventive plan is not currently due.",
        )
        generation_target = clean_text(
            getattr(candidate, "generation_target", generation_target),
            default=generation_target,
        )

    next_due_at = ensure_utc_datetime(getattr(plan, "next_due_at", None))
    next_due_counter = getattr(plan, "next_due_counter", None)
    is_due_soon = (
        due_state == "NOT_DUE"
        and next_due_at is not None
        and datetime.now(timezone.utc) <= next_due_at <= datetime.now(timezone.utc) + _PREVENTIVE_DUE_SOON_WINDOW
    )
    next_due_label = "-"
    if next_due_at is not None:
        next_due_label = format_timestamp_label(next_due_at)
    elif next_due_counter is not None:
        next_due_label = str(next_due_counter)
    elif due_state == "BLOCKED":
        next_due_label = "Review exception"
    if is_due_soon:
        due_state_label = "Due Soon"
    else:
        due_state_label = format_enum_label(due_state)

    return MaintenancePlannerPreventiveRowDescriptor(
        plan_id=plan.id,
        plan_code=clean_text(getattr(plan, "plan_code", "")),
        plan_name=clean_text(getattr(plan, "name", "")),
        plan_label=code_name_label(getattr(plan, "plan_code", ""), getattr(plan, "name", "")),
        anchor_label=planner_anchor_label(
            asset_id=getattr(plan, "asset_id", None),
            system_id=getattr(plan, "system_id", None),
            location_id=None,
            site_id=getattr(plan, "site_id", ""),
            site_lookup=site_lookup,
            asset_lookup=asset_lookup,
            system_lookup=system_lookup,
        ),
        due_state=due_state,
        due_state_label=due_state_label,
        due_reason=due_reason,
        generation_target=generation_target,
        generation_target_label=format_enum_label(generation_target),
        trigger_label=planner_trigger_label(plan),
        next_due_label=next_due_label,
        is_due_soon=is_due_soon,
    )


def serialize_recurring_row(
    row,
    *,
    exception_count_by_anchor: dict[str, int],
) -> MaintenancePlannerRecurringRowDescriptor:
    return MaintenancePlannerRecurringRowDescriptor(
        anchor_id=clean_text(getattr(row, "anchor_id", "")),
        anchor_label=code_name_label(
            getattr(row, "anchor_code", ""),
            getattr(row, "anchor_name", ""),
        ),
        failure_name=clean_text(getattr(row, "failure_name", ""), default="-"),
        leading_root_cause_name=clean_text(
            getattr(row, "leading_root_cause_name", ""),
            default="-",
        ),
        occurrence_count=int(getattr(row, "occurrence_count", 0) or 0),
        open_work_orders=int(getattr(row, "open_work_orders", 0) or 0),
        sensor_exception_count=exception_count_by_anchor.get(
            clean_text(getattr(row, "anchor_id", "")),
            0,
        ),
    )


def request_search_blob(row) -> str:
    return " ".join(
        filter(
            None,
            [
                getattr(row, "work_request_code", ""),
                getattr(row, "title", ""),
                getattr(row, "description", ""),
                getattr(row, "failure_symptom_code", ""),
                getattr(row, "request_type", ""),
                enum_value(getattr(row, "status", "")),
            ],
        )
    ).lower()


def work_order_search_blob(row) -> str:
    return " ".join(
        filter(
            None,
            [
                getattr(row, "work_order_code", ""),
                getattr(row, "title", ""),
                getattr(row, "description", ""),
                getattr(row, "failure_code", ""),
                getattr(row, "root_cause_code", ""),
                enum_value(getattr(row, "work_order_type", "")),
                enum_value(getattr(row, "status", "")),
            ],
        )
    ).lower()


def format_window_label(started_at, ended_at) -> str:
    if started_at is None and ended_at is None:
        return "-"
    return f"{format_timestamp_label(started_at)} -> {format_timestamp_label(ended_at)}"


def ensure_utc_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def planner_trigger_label(plan) -> str:
    trigger_mode = enum_value(getattr(plan, "trigger_mode", ""))
    if trigger_mode == "CALENDAR":
        frequency_unit = getattr(plan, "calendar_frequency_unit", None)
        frequency_value = getattr(plan, "calendar_frequency_value", None)
        if frequency_unit is None or frequency_value in (None, 0):
            return "Calendar"
        unit_value = clean_text(getattr(frequency_unit, "value", frequency_unit)).replace("_", " ").lower()
        return f"Every {frequency_value} {unit_value}"
    if trigger_mode == "SENSOR":
        return "Sensor threshold"
    return "Hybrid"


__all__ = [
    "ensure_utc_datetime",
    "format_timestamp_label",
    "format_window_label",
    "planner_trigger_label",
    "request_search_blob",
    "serialize_material_risk_row",
    "serialize_preventive_row",
    "serialize_recurring_row",
    "serialize_request_row",
    "serialize_work_order_row",
    "work_order_search_blob",
]
