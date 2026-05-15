from __future__ import annotations

from src.core.modules.maintenance.api.desktop._support import (
    clean_id,
    clean_text,
    datetime_text,
    enum_value,
    float_value,
    format_enum_label,
    int_value,
)
from src.core.modules.maintenance.api.desktop.work_orders.models import (
    MaintenanceSourceWorkRequestOptionDescriptor,
    MaintenanceWorkOrderDesktopDto,
)


def serialize_source_work_request_option(row) -> MaintenanceSourceWorkRequestOptionDescriptor:
    status = enum_value(getattr(row, "status", ""))
    priority = enum_value(getattr(row, "priority", ""))
    return MaintenanceSourceWorkRequestOptionDescriptor(
        value=row.id,
        label=source_work_request_label(row),
        site_id=row.site_id,
        asset_id=clean_id(getattr(row, "asset_id", None)),
        component_id=clean_id(getattr(row, "component_id", None)),
        system_id=clean_id(getattr(row, "system_id", None)),
        location_id=clean_id(getattr(row, "location_id", None)),
        status=status,
        status_label=format_enum_label(status),
        priority=priority,
        priority_label=format_enum_label(priority),
    )


def serialize_work_order(
    row,
    *,
    site_lookup: dict[str, str],
    location_lookup: dict[str, str],
    system_lookup: dict[str, str],
    asset_lookup: dict[str, str],
    component_lookup: dict[str, str],
    employee_lookup: dict[str, str],
    party_lookup: dict[str, str],
    source_lookup: dict[str, str],
) -> MaintenanceWorkOrderDesktopDto:
    work_order_type = enum_value(getattr(row, "work_order_type", ""))
    priority = enum_value(getattr(row, "priority", ""))
    status = enum_value(getattr(row, "status", ""))
    source_type = enum_value(getattr(row, "source_type", ""))
    source_id = clean_id(getattr(row, "source_id", None))
    asset_id = clean_id(getattr(row, "asset_id", None))
    component_id = clean_id(getattr(row, "component_id", None))
    system_id = clean_id(getattr(row, "system_id", None))
    location_id = clean_id(getattr(row, "location_id", None))
    assigned_employee_id = clean_id(getattr(row, "assigned_employee_id", None))
    vendor_party_id = clean_id(getattr(row, "vendor_party_id", None))
    requested_by_user_id = clean_id(getattr(row, "requested_by_user_id", None))
    planner_user_id = clean_id(getattr(row, "planner_user_id", None))
    supervisor_user_id = clean_id(getattr(row, "supervisor_user_id", None))
    assigned_team_id = clean_id(getattr(row, "assigned_team_id", None))
    return MaintenanceWorkOrderDesktopDto(
        id=row.id,
        site_id=row.site_id,
        site_label=site_lookup.get(row.site_id, "-"),
        work_order_code=clean_text(getattr(row, "work_order_code", "")),
        work_order_type=work_order_type,
        work_order_type_label=format_enum_label(work_order_type),
        source_type=source_type,
        source_type_label=format_enum_label(source_type),
        source_id=source_id,
        source_label=source_label(
            source_type=source_type,
            source_id=source_id,
            source_lookup=source_lookup,
        ),
        asset_id=asset_id,
        asset_label=asset_lookup.get(asset_id or "", "-"),
        component_id=component_id,
        component_label=component_lookup.get(component_id or "", "-"),
        system_id=system_id,
        system_label=system_lookup.get(system_id or "", "-"),
        location_id=location_id,
        location_label=location_lookup.get(location_id or "", "-"),
        title=clean_text(getattr(row, "title", "")),
        description=clean_text(getattr(row, "description", "")),
        priority=priority,
        priority_label=format_enum_label(priority),
        status=status,
        status_label=format_enum_label(status),
        requested_by_user_id=requested_by_user_id,
        planner_user_id=planner_user_id,
        supervisor_user_id=supervisor_user_id,
        assigned_team_id=assigned_team_id,
        assigned_employee_id=assigned_employee_id,
        assigned_employee_label=employee_lookup.get(assigned_employee_id or "", "-"),
        planned_start=datetime_text(getattr(row, "planned_start", None)),
        planned_end=datetime_text(getattr(row, "planned_end", None)),
        actual_start=datetime_text(getattr(row, "actual_start", None)),
        actual_end=datetime_text(getattr(row, "actual_end", None)),
        requires_shutdown=bool(getattr(row, "requires_shutdown", False)),
        permit_required=bool(getattr(row, "permit_required", False)),
        approval_required=bool(getattr(row, "approval_required", False)),
        failure_code=clean_text(getattr(row, "failure_code", "")),
        root_cause_code=clean_text(getattr(row, "root_cause_code", "")),
        downtime_minutes=int_value(getattr(row, "downtime_minutes", None)),
        parts_cost=float_value(getattr(row, "parts_cost", None)),
        labor_cost=float_value(getattr(row, "labor_cost", None)),
        vendor_party_id=vendor_party_id,
        vendor_party_label=party_lookup.get(vendor_party_id or "", "-"),
        is_preventive=bool(getattr(row, "is_preventive", False)),
        is_emergency=bool(getattr(row, "is_emergency", False)),
        closed_at=datetime_text(getattr(row, "closed_at", None)),
        closed_by_user_id=clean_id(getattr(row, "closed_by_user_id", None)),
        notes=clean_text(getattr(row, "notes", "")),
        version=int(getattr(row, "version", 0) or 0),
    )


def source_work_request_label(row) -> str:
    code = clean_text(getattr(row, "work_request_code", ""))
    title = clean_text(getattr(row, "title", ""))
    if code and title:
        return f"{code} - {title}"
    return code or title or "-"


def source_label(
    *,
    source_type: str,
    source_id: str | None,
    source_lookup: dict[str, str],
) -> str:
    if not source_id:
        return format_enum_label(source_type)
    if source_type == "WORK_REQUEST":
        return source_lookup.get(source_id, f"Work Request: {source_id}")
    return f"{format_enum_label(source_type)}: {source_id}"


__all__ = [
    "serialize_source_work_request_option",
    "serialize_work_order",
    "source_label",
    "source_work_request_label",
]
