from __future__ import annotations

from src.core.modules.maintenance.api.desktop._support import (
    clean_id,
    clean_text,
    datetime_text,
    enum_value,
    format_enum_label,
)
from src.core.modules.maintenance.api.desktop.work_requests.models import (
    MaintenanceWorkRequestDesktopDto,
)


def serialize_work_request(
    row,
    *,
    site_lookup: dict[str, str],
    location_lookup: dict[str, str],
    system_lookup: dict[str, str],
    asset_lookup: dict[str, str],
    component_lookup: dict[str, str],
) -> MaintenanceWorkRequestDesktopDto:
    source_type = enum_value(getattr(row, "source_type", ""))
    priority = enum_value(getattr(row, "priority", ""))
    status = enum_value(getattr(row, "status", ""))
    asset_id = clean_id(getattr(row, "asset_id", None))
    component_id = clean_id(getattr(row, "component_id", None))
    system_id = clean_id(getattr(row, "system_id", None))
    location_id = clean_id(getattr(row, "location_id", None))
    requested_by_user_id = clean_id(getattr(row, "requested_by_user_id", None))
    triaged_by_user_id = clean_id(getattr(row, "triaged_by_user_id", None))
    requested_by_name = clean_text(getattr(row, "requested_by_name_snapshot", ""))
    return MaintenanceWorkRequestDesktopDto(
        id=row.id,
        site_id=row.site_id,
        site_label=site_lookup.get(row.site_id, "-"),
        asset_id=asset_id,
        asset_label=asset_lookup.get(asset_id or "", "-"),
        component_id=component_id,
        component_label=component_lookup.get(component_id or "", "-"),
        system_id=system_id,
        system_label=system_lookup.get(system_id or "", "-"),
        location_id=location_id,
        location_label=location_lookup.get(location_id or "", "-"),
        work_request_code=clean_text(getattr(row, "work_request_code", "")),
        source_type=source_type,
        source_type_label=format_enum_label(source_type),
        request_type=clean_text(getattr(row, "request_type", "")),
        source_id=clean_id(getattr(row, "source_id", None)),
        title=clean_text(getattr(row, "title", "")),
        description=clean_text(getattr(row, "description", "")),
        priority=priority,
        priority_label=format_enum_label(priority),
        status=status,
        status_label=format_enum_label(status),
        requested_at=datetime_text(getattr(row, "requested_at", None)),
        requested_by_user_id=requested_by_user_id,
        requested_by_name=requested_by_name or "-",
        triaged_at=datetime_text(getattr(row, "triaged_at", None)),
        triaged_by_user_id=triaged_by_user_id,
        triaged_by_label=triaged_by_user_id or "-",
        failure_symptom_code=clean_text(getattr(row, "failure_symptom_code", "")),
        safety_risk_level=clean_text(getattr(row, "safety_risk_level", "")),
        production_impact_level=clean_text(getattr(row, "production_impact_level", "")),
        notes=clean_text(getattr(row, "notes", "")),
        version=int(getattr(row, "version", 0) or 0),
    )


def timestamp_sort_key(value) -> str:
    return datetime_text(value)


__all__ = [
    "serialize_work_request",
    "timestamp_sort_key",
]
