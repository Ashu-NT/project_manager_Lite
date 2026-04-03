from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from core.modules.maintenance_management.domain import (
    MaintenanceCriticality,
    MaintenanceLifecycleStatus,
    MaintenancePriority,
    MaintenanceTriggerMode,
    MaintenanceTaskCompletionRule,
    MaintenanceWorkOrderStatus,
    MaintenanceWorkOrderTaskStatus,
    MaintenanceWorkOrderType,
    MaintenanceWorkRequestSourceType,
    MaintenanceWorkRequestStatus,
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


def coerce_optional_date(value: date | str | None, *, label: str) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    raw = str(value).strip()
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValidationError(f"{label} is invalid. Use YYYY-MM-DD.", code=f"{label.upper().replace(' ', '_')}_INVALID") from exc


def coerce_optional_non_negative_int(value: int | str | None, *, label: str) -> int | None:
    if value in (None, ""):
        return None
    try:
        resolved = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{label} is invalid.", code=f"{label.upper().replace(' ', '_')}_INVALID") from exc
    if resolved < 0:
        raise ValidationError(f"{label} cannot be negative.", code=f"{label.upper().replace(' ', '_')}_NEGATIVE")
    return resolved


def coerce_optional_decimal(value: Decimal | int | float | str | None, *, label: str) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        resolved = value if isinstance(value, Decimal) else Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{label} is invalid.", code=f"{label.upper().replace(' ', '_')}_INVALID") from exc
    if resolved < 0:
        raise ValidationError(f"{label} cannot be negative.", code=f"{label.upper().replace(' ', '_')}_NEGATIVE")
    return resolved


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


def coerce_work_request_source_type(
    value: MaintenanceWorkRequestSourceType | str | None,
) -> MaintenanceWorkRequestSourceType:
    if isinstance(value, MaintenanceWorkRequestSourceType):
        return value
    raw = str(value or MaintenanceWorkRequestSourceType.MANUAL.value).strip().upper()
    try:
        return MaintenanceWorkRequestSourceType(raw)
    except ValueError as exc:
        raise ValidationError(
            "Maintenance work request source type is invalid.",
            code="MAINTENANCE_WORK_REQUEST_SOURCE_TYPE_INVALID",
        ) from exc


def coerce_work_request_status(
    value: MaintenanceWorkRequestStatus | str | None,
) -> MaintenanceWorkRequestStatus:
    if isinstance(value, MaintenanceWorkRequestStatus):
        return value
    raw = str(value or MaintenanceWorkRequestStatus.NEW.value).strip().upper()
    try:
        return MaintenanceWorkRequestStatus(raw)
    except ValueError as exc:
        raise ValidationError(
            "Maintenance work request status is invalid.",
            code="MAINTENANCE_WORK_REQUEST_STATUS_INVALID",
        ) from exc


def coerce_work_order_type(value: MaintenanceWorkOrderType | str | None) -> MaintenanceWorkOrderType:
    if isinstance(value, MaintenanceWorkOrderType):
        return value
    raw = str(value or MaintenanceWorkOrderType.CORRECTIVE.value).strip().upper()
    try:
        return MaintenanceWorkOrderType(raw)
    except ValueError as exc:
        raise ValidationError(
            "Maintenance work order type is invalid.",
            code="MAINTENANCE_WORK_ORDER_TYPE_INVALID",
        ) from exc


def coerce_work_order_status(
    value: MaintenanceWorkOrderStatus | str | None,
) -> MaintenanceWorkOrderStatus:
    if isinstance(value, MaintenanceWorkOrderStatus):
        return value
    raw = str(value or MaintenanceWorkOrderStatus.DRAFT.value).strip().upper()
    try:
        return MaintenanceWorkOrderStatus(raw)
    except ValueError as exc:
        raise ValidationError(
            "Maintenance work order status is invalid.",
            code="MAINTENANCE_WORK_ORDER_STATUS_INVALID",
        ) from exc


def coerce_work_order_task_status(
    value: MaintenanceWorkOrderTaskStatus | str | None,
) -> MaintenanceWorkOrderTaskStatus:
    if isinstance(value, MaintenanceWorkOrderTaskStatus):
        return value
    raw = str(value or MaintenanceWorkOrderTaskStatus.NOT_STARTED.value).strip().upper()
    try:
        return MaintenanceWorkOrderTaskStatus(raw)
    except ValueError as exc:
        raise ValidationError(
            "Maintenance work order task status is invalid.",
            code="MAINTENANCE_WORK_ORDER_TASK_STATUS_INVALID",
        ) from exc


def coerce_task_completion_rule(
    value: MaintenanceTaskCompletionRule | str | None,
) -> MaintenanceTaskCompletionRule:
    if isinstance(value, MaintenanceTaskCompletionRule):
        return value
    raw = str(value or MaintenanceTaskCompletionRule.NO_STEPS_REQUIRED.value).strip().upper()
    try:
        return MaintenanceTaskCompletionRule(raw)
    except ValueError as exc:
        raise ValidationError(
            "Maintenance task completion rule is invalid.",
            code="MAINTENANCE_TASK_COMPLETION_RULE_INVALID",
        ) from exc


__all__ = [
    "coerce_criticality",
    "coerce_lifecycle_status",
    "coerce_optional_date",
    "coerce_optional_decimal",
    "coerce_optional_non_negative_int",
    "coerce_priority",
    "coerce_task_completion_rule",
    "coerce_trigger_mode",
    "coerce_work_order_status",
    "coerce_work_order_task_status",
    "coerce_work_order_type",
    "coerce_work_request_source_type",
    "coerce_work_request_status",
    "normalize_maintenance_code",
    "normalize_maintenance_name",
    "normalize_optional_text",
]
