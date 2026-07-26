from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import TypeVar

from src.core.modules.maintenance.domain.enums import (
    MaintenanceCalendarFrequencyUnit,
    MaintenanceMaterialProcurementStatus,
    MaintenanceCriticality,
    MaintenanceFailureCodeType,
    MaintenanceGenerationLeadUnit,
    MaintenanceLifecycleStatus,
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
    MaintenanceTaskCompletionRule,
    MaintenanceTemplateStatus,
    MaintenanceTriggerMode,
    MaintenanceWorkOrderStatus,
    MaintenanceWorkOrderTaskStatus,
    MaintenanceWorkOrderTaskStepStatus,
    MaintenanceWorkOrderType,
    MaintenanceWorkRequestSourceType,
    MaintenanceWorkRequestStatus,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_optional_text,
    normalize_required_text,
)


def _label_code(label: str, suffix: str) -> str:
    return f"{label.upper().replace(' ', '_')}_{suffix}"


EnumT = TypeVar("EnumT", bound=Enum)


def _normalize_enum(
    value: object,
    *,
    enum_type: type[EnumT],
    default: EnumT,
    message: str,
    code: str,
) -> EnumT:
    if isinstance(value, enum_type):
        return value
    raw = normalize_optional_upper_text(value)
    if not raw:
        return default
    try:
        return enum_type(raw)
    except ValueError as exc:
        raise ValidationError(message, code=code) from exc


def normalize_maintenance_code(value: object, *, label: str) -> str:
    return normalize_required_text(
        value,
        message=f"{label} is required.",
        code=_label_code(label, "REQUIRED"),
    ).upper()


def normalize_maintenance_name(value: object, *, label: str) -> str:
    return normalize_required_text(
        value,
        message=f"{label} is required.",
        code=_label_code(label, "REQUIRED"),
    )


def normalize_optional_upper_text(value: object) -> str:
    return normalize_optional_text(value).upper()


def normalize_identifier_tuple(value: object) -> tuple[str, ...]:
    if value in (None, ""):
        return ()
    if isinstance(value, (list, tuple, set, frozenset)):
        items = value
    else:
        items = (value,)
    normalized: list[str] = []
    for item in items:
        candidate = normalize_optional_identifier(item)
        if candidate:
            normalized.append(candidate)
    return tuple(normalized)


def normalize_optional_date(value: object, *, label: str) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = normalize_optional_text(value)
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValidationError(
            f"{label} is invalid. Use YYYY-MM-DD.",
            code=_label_code(label, "INVALID"),
        ) from exc


def normalize_optional_datetime(
    value: object,
    *,
    message: str,
    code: str,
) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        resolved = value
    else:
        raw = normalize_optional_text(value)
        try:
            resolved = datetime.fromisoformat(raw)
        except ValueError as exc:
            raise ValidationError(message, code=code) from exc
    if resolved.tzinfo is None or resolved.utcoffset() is None:
        return resolved.replace(tzinfo=timezone.utc)
    return resolved.astimezone(timezone.utc)


def normalize_positive_int(
    value: object,
    *,
    message: str,
    code: str,
    default: int = 1,
) -> int:
    raw = default if value in (None, "") else value
    try:
        resolved = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError(message, code=code) from exc
    if resolved < 1:
        raise ValidationError(message, code=code)
    return resolved


def normalize_optional_non_negative_int(value: object, *, label: str) -> int | None:
    if value in (None, ""):
        return None
    try:
        resolved = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            f"{label} is invalid.",
            code=_label_code(label, "INVALID"),
        ) from exc
    if resolved < 0:
        raise ValidationError(
            f"{label} cannot be negative.",
            code=_label_code(label, "NEGATIVE"),
        )
    return resolved


def normalize_optional_decimal(value: object, *, label: str) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        resolved = value if isinstance(value, Decimal) else Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(
            f"{label} is invalid.",
            code=_label_code(label, "INVALID"),
        ) from exc
    if resolved < 0:
        raise ValidationError(
            f"{label} cannot be negative.",
            code=_label_code(label, "NEGATIVE"),
        )
    return resolved


def normalize_optional_decimal_value(value: object, *, label: str) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return value if isinstance(value, Decimal) else Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(
            f"{label} is invalid.",
            code=_label_code(label, "INVALID"),
        ) from exc


def normalize_positive_decimal(value: object, *, label: str) -> Decimal:
    resolved = normalize_optional_decimal(value, label=label)
    if resolved is None or resolved <= 0:
        raise ValidationError(
            f"{label} must be greater than zero.",
            code=_label_code(label, "POSITIVE_REQUIRED"),
        )
    return resolved


def normalize_criticality(value: object) -> MaintenanceCriticality:
    if isinstance(value, MaintenanceCriticality):
        return value
    raw = normalize_optional_upper_text(value) or MaintenanceCriticality.MEDIUM.value
    try:
        return MaintenanceCriticality(raw)
    except ValueError as exc:
        raise ValidationError(
            "Criticality is invalid.",
            code="MAINTENANCE_CRITICALITY_INVALID",
        ) from exc


def normalize_lifecycle_status(
    value: object,
    *,
    is_active: bool = True,
) -> MaintenanceLifecycleStatus:
    if value in (None, ""):
        return (
            MaintenanceLifecycleStatus.ACTIVE
            if is_active
            else MaintenanceLifecycleStatus.INACTIVE
        )
    if isinstance(value, MaintenanceLifecycleStatus):
        return value
    raw = normalize_optional_upper_text(value)
    try:
        return MaintenanceLifecycleStatus(raw)
    except ValueError as exc:
        raise ValidationError(
            "Maintenance lifecycle status is invalid.",
            code="MAINTENANCE_STATUS_INVALID",
        ) from exc


def normalize_priority(value: object) -> MaintenancePriority:
    return _normalize_enum(
        value,
        enum_type=MaintenancePriority,
        default=MaintenancePriority.MEDIUM,
        message="Maintenance priority is invalid.",
        code="MAINTENANCE_PRIORITY_INVALID",
    )


def normalize_work_request_source_type(
    value: object,
) -> MaintenanceWorkRequestSourceType:
    return _normalize_enum(
        value,
        enum_type=MaintenanceWorkRequestSourceType,
        default=MaintenanceWorkRequestSourceType.MANUAL,
        message="Maintenance work request source type is invalid.",
        code="MAINTENANCE_WORK_REQUEST_SOURCE_TYPE_INVALID",
    )


def normalize_work_request_status(value: object) -> MaintenanceWorkRequestStatus:
    return _normalize_enum(
        value,
        enum_type=MaintenanceWorkRequestStatus,
        default=MaintenanceWorkRequestStatus.NEW,
        message="Maintenance work request status is invalid.",
        code="MAINTENANCE_WORK_REQUEST_STATUS_INVALID",
    )


def normalize_work_order_type(value: object) -> MaintenanceWorkOrderType:
    return _normalize_enum(
        value,
        enum_type=MaintenanceWorkOrderType,
        default=MaintenanceWorkOrderType.CORRECTIVE,
        message="Maintenance work order type is invalid.",
        code="MAINTENANCE_WORK_ORDER_TYPE_INVALID",
    )


def normalize_work_order_status(value: object) -> MaintenanceWorkOrderStatus:
    return _normalize_enum(
        value,
        enum_type=MaintenanceWorkOrderStatus,
        default=MaintenanceWorkOrderStatus.DRAFT,
        message="Maintenance work order status is invalid.",
        code="MAINTENANCE_WORK_ORDER_STATUS_INVALID",
    )


def normalize_work_order_task_status(value: object) -> MaintenanceWorkOrderTaskStatus:
    return _normalize_enum(
        value,
        enum_type=MaintenanceWorkOrderTaskStatus,
        default=MaintenanceWorkOrderTaskStatus.NOT_STARTED,
        message="Maintenance work order task status is invalid.",
        code="MAINTENANCE_WORK_ORDER_TASK_STATUS_INVALID",
    )


def normalize_task_completion_rule(value: object) -> MaintenanceTaskCompletionRule:
    return _normalize_enum(
        value,
        enum_type=MaintenanceTaskCompletionRule,
        default=MaintenanceTaskCompletionRule.NO_STEPS_REQUIRED,
        message="Maintenance task completion rule is invalid.",
        code="MAINTENANCE_TASK_COMPLETION_RULE_INVALID",
    )


def normalize_work_order_task_step_status(
    value: object,
) -> MaintenanceWorkOrderTaskStepStatus:
    return _normalize_enum(
        value,
        enum_type=MaintenanceWorkOrderTaskStepStatus,
        default=MaintenanceWorkOrderTaskStepStatus.NOT_STARTED,
        message="Maintenance work order task step status is invalid.",
        code="MAINTENANCE_WORK_ORDER_TASK_STEP_STATUS_INVALID",
    )


def normalize_material_procurement_status(
    value: object,
    *,
    is_stock_item: bool = True,
) -> MaintenanceMaterialProcurementStatus:
    default = (
        MaintenanceMaterialProcurementStatus.PLANNED
        if is_stock_item
        else MaintenanceMaterialProcurementStatus.NON_STOCK
    )
    return _normalize_enum(
        value,
        enum_type=MaintenanceMaterialProcurementStatus,
        default=default,
        message="Maintenance material procurement status is invalid.",
        code="MAINTENANCE_MATERIAL_PROCUREMENT_STATUS_INVALID",
    )


def normalize_sensor_quality_state(value: object) -> MaintenanceSensorQualityState:
    return _normalize_enum(
        value,
        enum_type=MaintenanceSensorQualityState,
        default=MaintenanceSensorQualityState.VALID,
        message="Maintenance sensor quality state is invalid.",
        code="MAINTENANCE_SENSOR_QUALITY_STATE_INVALID",
    )


def normalize_sensor_exception_type(value: object) -> MaintenanceSensorExceptionType:
    return _normalize_enum(
        value,
        enum_type=MaintenanceSensorExceptionType,
        default=MaintenanceSensorExceptionType.STALE_READING,
        message="Maintenance sensor exception type is invalid.",
        code="MAINTENANCE_SENSOR_EXCEPTION_TYPE_INVALID",
    )


def normalize_sensor_exception_status(value: object) -> MaintenanceSensorExceptionStatus:
    return _normalize_enum(
        value,
        enum_type=MaintenanceSensorExceptionStatus,
        default=MaintenanceSensorExceptionStatus.OPEN,
        message="Maintenance sensor exception status is invalid.",
        code="MAINTENANCE_SENSOR_EXCEPTION_STATUS_INVALID",
    )


def normalize_failure_code_type(value: object) -> MaintenanceFailureCodeType:
    return _normalize_enum(
        value,
        enum_type=MaintenanceFailureCodeType,
        default=MaintenanceFailureCodeType.SYMPTOM,
        message="Maintenance failure code type is invalid.",
        code="MAINTENANCE_FAILURE_CODE_TYPE_INVALID",
    )


def normalize_template_status(value: object) -> MaintenanceTemplateStatus:
    return _normalize_enum(
        value,
        enum_type=MaintenanceTemplateStatus,
        default=MaintenanceTemplateStatus.DRAFT,
        message="Maintenance template status is invalid.",
        code="MAINTENANCE_TEMPLATE_STATUS_INVALID",
    )


def normalize_plan_status(value: object) -> MaintenancePlanStatus:
    return _normalize_enum(
        value,
        enum_type=MaintenancePlanStatus,
        default=MaintenancePlanStatus.DRAFT,
        message="Maintenance plan status is invalid.",
        code="MAINTENANCE_PLAN_STATUS_INVALID",
    )


def normalize_plan_type(value: object) -> MaintenancePlanType:
    return _normalize_enum(
        value,
        enum_type=MaintenancePlanType,
        default=MaintenancePlanType.PREVENTIVE,
        message="Maintenance plan type is invalid.",
        code="MAINTENANCE_PLAN_TYPE_INVALID",
    )


def normalize_trigger_mode(value: object) -> MaintenanceTriggerMode:
    return _normalize_enum(
        value,
        enum_type=MaintenanceTriggerMode,
        default=MaintenanceTriggerMode.CALENDAR,
        message="Maintenance trigger mode is invalid.",
        code="MAINTENANCE_TRIGGER_MODE_INVALID",
    )


def normalize_schedule_policy(value: object) -> MaintenanceSchedulePolicy:
    return _normalize_enum(
        value,
        enum_type=MaintenanceSchedulePolicy,
        default=MaintenanceSchedulePolicy.FIXED,
        message="Maintenance schedule policy is invalid.",
        code="MAINTENANCE_SCHEDULE_POLICY_INVALID",
    )


def normalize_calendar_frequency_unit(
    value: object,
) -> MaintenanceCalendarFrequencyUnit | None:
    if value in (None, ""):
        return None
    return _normalize_enum(
        value,
        enum_type=MaintenanceCalendarFrequencyUnit,
        default=MaintenanceCalendarFrequencyUnit.DAILY,
        message="Maintenance calendar frequency unit is invalid.",
        code="MAINTENANCE_CALENDAR_FREQUENCY_UNIT_INVALID",
    )


def normalize_generation_lead_unit(value: object) -> MaintenanceGenerationLeadUnit:
    return _normalize_enum(
        value,
        enum_type=MaintenanceGenerationLeadUnit,
        default=MaintenanceGenerationLeadUnit.DAYS,
        message="Maintenance generation lead unit is invalid.",
        code="MAINTENANCE_GENERATION_LEAD_UNIT_INVALID",
    )


def normalize_sensor_direction(value: object) -> MaintenanceSensorDirection | None:
    if value in (None, ""):
        return None
    return _normalize_enum(
        value,
        enum_type=MaintenanceSensorDirection,
        default=MaintenanceSensorDirection.GREATER_OR_EQUAL,
        message="Maintenance sensor direction is invalid.",
        code="MAINTENANCE_SENSOR_DIRECTION_INVALID",
    )


def normalize_plan_task_trigger_scope(
    value: object,
) -> MaintenancePlanTaskTriggerScope:
    return _normalize_enum(
        value,
        enum_type=MaintenancePlanTaskTriggerScope,
        default=MaintenancePlanTaskTriggerScope.INHERIT_PLAN,
        message="Maintenance plan task trigger scope is invalid.",
        code="MAINTENANCE_PLAN_TASK_TRIGGER_SCOPE_INVALID",
    )


def normalize_preventive_instance_status(
    value: object,
) -> MaintenancePreventiveInstanceStatus:
    return _normalize_enum(
        value,
        enum_type=MaintenancePreventiveInstanceStatus,
        default=MaintenancePreventiveInstanceStatus.PLANNED,
        message="Maintenance preventive instance status is invalid.",
        code="MAINTENANCE_PREVENTIVE_INSTANCE_STATUS_INVALID",
    )


__all__ = [
    "normalize_criticality",
    "normalize_identifier_tuple",
    "normalize_lifecycle_status",
    "normalize_material_procurement_status",
    "normalize_maintenance_code",
    "normalize_maintenance_name",
    "normalize_failure_code_type",
    "normalize_calendar_frequency_unit",
    "normalize_generation_lead_unit",
    "normalize_optional_date",
    "normalize_optional_datetime",
    "normalize_optional_decimal",
    "normalize_optional_decimal_value",
    "normalize_optional_identifier",
    "normalize_optional_non_negative_int",
    "normalize_optional_text",
    "normalize_optional_upper_text",
    "normalize_positive_decimal",
    "normalize_positive_int",
    "normalize_plan_status",
    "normalize_plan_task_trigger_scope",
    "normalize_plan_type",
    "normalize_preventive_instance_status",
    "normalize_priority",
    "normalize_required_text",
    "normalize_schedule_policy",
    "normalize_sensor_direction",
    "normalize_sensor_exception_status",
    "normalize_sensor_exception_type",
    "normalize_sensor_quality_state",
    "normalize_task_completion_rule",
    "normalize_template_status",
    "normalize_trigger_mode",
    "normalize_work_order_status",
    "normalize_work_order_task_status",
    "normalize_work_order_task_step_status",
    "normalize_work_order_type",
    "normalize_work_request_source_type",
    "normalize_work_request_status",
]
