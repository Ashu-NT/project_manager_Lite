from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

from core.modules.maintenance_management.domain import (
    MaintenanceCalendarFrequencyUnit,
    MaintenanceCriticality,
    MaintenanceFailureCodeType,
    MaintenanceLifecycleStatus,
    MaintenanceMaterialProcurementStatus,
    MaintenancePlanStatus,
    MaintenancePlanTaskTriggerScope,
    MaintenancePlanType,
    MaintenancePreventiveInstanceStatus,
    MaintenancePriority,
    MaintenanceSchedulePolicy,
    MaintenanceSensorDirection,
    MaintenanceSensorExceptionStatus,
    MaintenanceSensorExceptionType,
    MaintenanceSensorQualityState,
    MaintenanceTemplateStatus,
    MaintenanceTriggerMode,
    MaintenanceTaskCompletionRule,
    MaintenanceWorkOrderTaskStepStatus,
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


def coerce_optional_datetime(value: datetime | str | None, *, label: str) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        resolved = value
    else:
        raw = str(value).strip()
        try:
            resolved = datetime.fromisoformat(raw)
        except ValueError as exc:
            raise ValidationError(
                f"{label} is invalid. Use ISO datetime format.",
                code=f"{label.upper().replace(' ', '_')}_INVALID",
            ) from exc
    if resolved.tzinfo is None:
        return resolved.replace(tzinfo=timezone.utc)
    return resolved.astimezone(timezone.utc)


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


def coerce_decimal_value(value: Decimal | int | float | str, *, label: str) -> Decimal:
    if value in (None, ""):
        raise ValidationError(f"{label} is required.", code=f"{label.upper().replace(' ', '_')}_REQUIRED")
    try:
        return value if isinstance(value, Decimal) else Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{label} is invalid.", code=f"{label.upper().replace(' ', '_')}_INVALID") from exc


def coerce_optional_decimal_value(value: Decimal | int | float | str | None, *, label: str) -> Decimal | None:
    if value in (None, ""):
        return None
    return coerce_decimal_value(value, label=label)


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


def coerce_template_status(value: MaintenanceTemplateStatus | str | None) -> MaintenanceTemplateStatus:
    if isinstance(value, MaintenanceTemplateStatus):
        return value
    raw = str(value or MaintenanceTemplateStatus.DRAFT.value).strip().upper()
    try:
        return MaintenanceTemplateStatus(raw)
    except ValueError as exc:
        raise ValidationError("Maintenance template status is invalid.", code="MAINTENANCE_TEMPLATE_STATUS_INVALID") from exc


def coerce_plan_status(value: MaintenancePlanStatus | str | None) -> MaintenancePlanStatus:
    if isinstance(value, MaintenancePlanStatus):
        return value
    raw = str(value or MaintenancePlanStatus.DRAFT.value).strip().upper()
    try:
        return MaintenancePlanStatus(raw)
    except ValueError as exc:
        raise ValidationError("Maintenance plan status is invalid.", code="MAINTENANCE_PLAN_STATUS_INVALID") from exc


def coerce_plan_type(value: MaintenancePlanType | str | None) -> MaintenancePlanType:
    if isinstance(value, MaintenancePlanType):
        return value
    raw = str(value or MaintenancePlanType.PREVENTIVE.value).strip().upper()
    try:
        return MaintenancePlanType(raw)
    except ValueError as exc:
        raise ValidationError("Maintenance plan type is invalid.", code="MAINTENANCE_PLAN_TYPE_INVALID") from exc


def coerce_schedule_policy(value: MaintenanceSchedulePolicy | str | None) -> MaintenanceSchedulePolicy:
    if isinstance(value, MaintenanceSchedulePolicy):
        return value
    raw = str(value or MaintenanceSchedulePolicy.FIXED.value).strip().upper()
    try:
        return MaintenanceSchedulePolicy(raw)
    except ValueError as exc:
        raise ValidationError(
            "Maintenance schedule policy is invalid.",
            code="MAINTENANCE_SCHEDULE_POLICY_INVALID",
        ) from exc


def coerce_calendar_frequency_unit(
    value: MaintenanceCalendarFrequencyUnit | str | None,
) -> MaintenanceCalendarFrequencyUnit | None:
    if value in (None, ""):
        return None
    if isinstance(value, MaintenanceCalendarFrequencyUnit):
        return value
    raw = str(value).strip().upper()
    try:
        return MaintenanceCalendarFrequencyUnit(raw)
    except ValueError as exc:
        raise ValidationError(
            "Maintenance calendar frequency unit is invalid.",
            code="MAINTENANCE_CALENDAR_FREQUENCY_UNIT_INVALID",
        ) from exc


def coerce_sensor_direction(
    value: MaintenanceSensorDirection | str | None,
) -> MaintenanceSensorDirection | None:
    if value in (None, ""):
        return None
    if isinstance(value, MaintenanceSensorDirection):
        return value
    raw = str(value).strip().upper()
    try:
        return MaintenanceSensorDirection(raw)
    except ValueError as exc:
        raise ValidationError(
            "Maintenance sensor direction is invalid.",
            code="MAINTENANCE_SENSOR_DIRECTION_INVALID",
        ) from exc


def coerce_plan_task_trigger_scope(
    value: MaintenancePlanTaskTriggerScope | str | None,
) -> MaintenancePlanTaskTriggerScope:
    if isinstance(value, MaintenancePlanTaskTriggerScope):
        return value
    raw = str(value or MaintenancePlanTaskTriggerScope.INHERIT_PLAN.value).strip().upper()
    try:
        return MaintenancePlanTaskTriggerScope(raw)
    except ValueError as exc:
        raise ValidationError(
            "Maintenance plan task trigger scope is invalid.",
            code="MAINTENANCE_PLAN_TASK_TRIGGER_SCOPE_INVALID",
        ) from exc


def coerce_preventive_instance_status(
    value: MaintenancePreventiveInstanceStatus | str | None,
) -> MaintenancePreventiveInstanceStatus:
    if isinstance(value, MaintenancePreventiveInstanceStatus):
        return value
    raw = str(value or MaintenancePreventiveInstanceStatus.PLANNED.value).strip().upper()
    try:
        return MaintenancePreventiveInstanceStatus(raw)
    except ValueError as exc:
        raise ValidationError(
            "Maintenance preventive instance status is invalid.",
            code="MAINTENANCE_PREVENTIVE_INSTANCE_STATUS_INVALID",
        ) from exc


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


def coerce_work_order_task_step_status(
    value: MaintenanceWorkOrderTaskStepStatus | str | None,
) -> MaintenanceWorkOrderTaskStepStatus:
    if isinstance(value, MaintenanceWorkOrderTaskStepStatus):
        return value
    raw = str(value or MaintenanceWorkOrderTaskStepStatus.NOT_STARTED.value).strip().upper()
    try:
        return MaintenanceWorkOrderTaskStepStatus(raw)
    except ValueError as exc:
        raise ValidationError(
            "Maintenance work order task step status is invalid.",
            code="MAINTENANCE_WORK_ORDER_TASK_STEP_STATUS_INVALID",
        ) from exc


def coerce_material_procurement_status(
    value: MaintenanceMaterialProcurementStatus | str | None,
) -> MaintenanceMaterialProcurementStatus:
    if isinstance(value, MaintenanceMaterialProcurementStatus):
        return value
    raw = str(value or MaintenanceMaterialProcurementStatus.PLANNED.value).strip().upper()
    try:
        return MaintenanceMaterialProcurementStatus(raw)
    except ValueError as exc:
        raise ValidationError(
            "Maintenance material procurement status is invalid.",
            code="MAINTENANCE_MATERIAL_PROCUREMENT_STATUS_INVALID",
        ) from exc


def coerce_sensor_quality_state(
    value: MaintenanceSensorQualityState | str | None,
) -> MaintenanceSensorQualityState:
    if isinstance(value, MaintenanceSensorQualityState):
        return value
    raw = str(value or MaintenanceSensorQualityState.VALID.value).strip().upper()
    try:
        return MaintenanceSensorQualityState(raw)
    except ValueError as exc:
        raise ValidationError(
            "Maintenance sensor quality state is invalid.",
            code="MAINTENANCE_SENSOR_QUALITY_STATE_INVALID",
        ) from exc


def coerce_sensor_exception_type(
    value: MaintenanceSensorExceptionType | str | None,
) -> MaintenanceSensorExceptionType:
    if isinstance(value, MaintenanceSensorExceptionType):
        return value
    raw = str(value or MaintenanceSensorExceptionType.STALE_READING.value).strip().upper()
    try:
        return MaintenanceSensorExceptionType(raw)
    except ValueError as exc:
        raise ValidationError(
            "Maintenance sensor exception type is invalid.",
            code="MAINTENANCE_SENSOR_EXCEPTION_TYPE_INVALID",
        ) from exc


def coerce_sensor_exception_status(
    value: MaintenanceSensorExceptionStatus | str | None,
) -> MaintenanceSensorExceptionStatus:
    if isinstance(value, MaintenanceSensorExceptionStatus):
        return value
    raw = str(value or MaintenanceSensorExceptionStatus.OPEN.value).strip().upper()
    try:
        return MaintenanceSensorExceptionStatus(raw)
    except ValueError as exc:
        raise ValidationError(
            "Maintenance sensor exception status is invalid.",
            code="MAINTENANCE_SENSOR_EXCEPTION_STATUS_INVALID",
        ) from exc


def coerce_failure_code_type(
    value: MaintenanceFailureCodeType | str | None,
) -> MaintenanceFailureCodeType:
    if isinstance(value, MaintenanceFailureCodeType):
        return value
    raw = str(value or MaintenanceFailureCodeType.SYMPTOM.value).strip().upper()
    try:
        return MaintenanceFailureCodeType(raw)
    except ValueError as exc:
        raise ValidationError(
            "Maintenance failure code type is invalid.",
            code="MAINTENANCE_FAILURE_CODE_TYPE_INVALID",
        ) from exc


def calculate_downtime_minutes(
    started_at: datetime,
    ended_at: datetime | None,
) -> int | None:
    if ended_at is None:
        return None
    if ended_at < started_at:
        raise ValidationError(
            "Downtime end cannot be earlier than downtime start.",
            code="MAINTENANCE_DOWNTIME_RANGE_INVALID",
        )
    total_seconds = max(0.0, (ended_at - started_at).total_seconds())
    return int((total_seconds + 59) // 60)


__all__ = [
    "coerce_criticality",
    "coerce_calendar_frequency_unit",
    "coerce_decimal_value",
    "coerce_material_procurement_status",
    "coerce_lifecycle_status",
    "coerce_optional_date",
    "coerce_optional_decimal",
    "coerce_optional_decimal_value",
    "coerce_optional_datetime",
    "coerce_optional_non_negative_int",
    "coerce_plan_status",
    "coerce_plan_task_trigger_scope",
    "coerce_plan_type",
    "coerce_priority",
    "coerce_sensor_direction",
    "coerce_sensor_exception_status",
    "coerce_sensor_exception_type",
    "coerce_sensor_quality_state",
    "coerce_task_completion_rule",
    "coerce_template_status",
    "coerce_work_order_task_step_status",
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
