from __future__ import annotations

from core.modules.maintenance_management.domain import (
    MaintenanceCriticality,
    MaintenanceLifecycleStatus,
    MaintenancePriority,
    MaintenanceTriggerMode,
)
from core.platform.common.exceptions import ValidationError


def normalize_maintenance_code(value: str, *, label: str) -> str:
    normalized = (value or "").strip().upper()
    if not normalized:
        raise ValidationError(f"{label} is required.", code=f"{label.upper().replace(' ', '_')}_REQUIRED")
    return normalized


def normalize_maintenance_name(value: str, *, label: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise ValidationError(f"{label} is required.", code=f"{label.upper().replace(' ', '_')}_REQUIRED")
    return normalized


def normalize_optional_text(value: str | None) -> str:
    return (value or "").strip()


def coerce_criticality(value: MaintenanceCriticality | str | None) -> MaintenanceCriticality:
    if isinstance(value, MaintenanceCriticality):
        return value
    raw = str(value or MaintenanceCriticality.MEDIUM.value).strip().upper()
    try:
        return MaintenanceCriticality(raw)
    except ValueError as exc:
        raise ValidationError("Criticality is invalid.", code="MAINTENANCE_CRITICALITY_INVALID") from exc


def coerce_lifecycle_status(
    value: MaintenanceLifecycleStatus | str | None,
    *,
    is_active: bool = True,
) -> MaintenanceLifecycleStatus:
    if isinstance(value, MaintenanceLifecycleStatus):
        return value
    raw = str(value or "").strip().upper()
    if not raw:
        return MaintenanceLifecycleStatus.ACTIVE if is_active else MaintenanceLifecycleStatus.INACTIVE
    try:
        return MaintenanceLifecycleStatus(raw)
    except ValueError as exc:
        raise ValidationError("Maintenance lifecycle status is invalid.", code="MAINTENANCE_STATUS_INVALID") from exc


def coerce_priority(value: MaintenancePriority | str | None) -> MaintenancePriority:
    if isinstance(value, MaintenancePriority):
        return value
    raw = str(value or MaintenancePriority.MEDIUM.value).strip().upper()
    try:
        return MaintenancePriority(raw)
    except ValueError as exc:
        raise ValidationError("Maintenance priority is invalid.", code="MAINTENANCE_PRIORITY_INVALID") from exc


def coerce_trigger_mode(value: MaintenanceTriggerMode | str | None) -> MaintenanceTriggerMode:
    if isinstance(value, MaintenanceTriggerMode):
        return value
    raw = str(value or MaintenanceTriggerMode.CALENDAR.value).strip().upper()
    try:
        return MaintenanceTriggerMode(raw)
    except ValueError as exc:
        raise ValidationError("Maintenance trigger mode is invalid.", code="MAINTENANCE_TRIGGER_MODE_INVALID") from exc


__all__ = [
    "coerce_criticality",
    "coerce_lifecycle_status",
    "coerce_priority",
    "coerce_trigger_mode",
    "normalize_maintenance_code",
    "normalize_maintenance_name",
    "normalize_optional_text",
]
