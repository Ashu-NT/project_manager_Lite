from __future__ import annotations

from enum import Enum


class MaintenanceLifecycleStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    RETIRED = "RETIRED"


class MaintenanceCriticality(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class MaintenancePriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EMERGENCY = "EMERGENCY"


class MaintenanceTriggerMode(str, Enum):
    CALENDAR = "CALENDAR"
    SENSOR = "SENSOR"
    HYBRID = "HYBRID"


class MaintenanceWorkRequestSourceType(str, Enum):
    MANUAL = "MANUAL"
    PREVENTIVE_PLAN = "PREVENTIVE_PLAN"
    SENSOR_TRIGGER = "SENSOR_TRIGGER"
    INSPECTION = "INSPECTION"
    INTEGRATION = "INTEGRATION"


class MaintenanceWorkRequestStatus(str, Enum):
    NEW = "NEW"
    TRIAGED = "TRIAGED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CONVERTED = "CONVERTED"
    DEFERRED = "DEFERRED"


class MaintenanceWorkOrderType(str, Enum):
    CORRECTIVE = "CORRECTIVE"
    PREVENTIVE = "PREVENTIVE"
    INSPECTION = "INSPECTION"
    CALIBRATION = "CALIBRATION"
    EMERGENCY = "EMERGENCY"
    CONDITION_BASED = "CONDITION_BASED"


class MaintenanceWorkOrderStatus(str, Enum):
    DRAFT = "DRAFT"
    PLANNED = "PLANNED"
    WAITING_PARTS = "WAITING_PARTS"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    WAITING_SHUTDOWN = "WAITING_SHUTDOWN"
    SCHEDULED = "SCHEDULED"
    RELEASED = "RELEASED"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    VERIFIED = "VERIFIED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class MaintenanceWorkOrderTaskStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    SKIPPED = "SKIPPED"


class MaintenanceTaskCompletionRule(str, Enum):
    NO_STEPS_REQUIRED = "NO_STEPS_REQUIRED"
    ALL_STEPS_REQUIRED = "ALL_STEPS_REQUIRED"


class MaintenanceWorkOrderTaskStepStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"


class MaintenanceMaterialProcurementStatus(str, Enum):
    PLANNED = "PLANNED"
    AVAILABLE_FROM_STOCK = "AVAILABLE_FROM_STOCK"
    SHORTAGE_IDENTIFIED = "SHORTAGE_IDENTIFIED"
    REQUISITIONED = "REQUISITIONED"
    PARTIALLY_ISSUED = "PARTIALLY_ISSUED"
    FULLY_ISSUED = "FULLY_ISSUED"
    NON_STOCK = "NON_STOCK"


class MaintenanceSensorQualityState(str, Enum):
    VALID = "VALID"
    STALE = "STALE"
    ESTIMATED = "ESTIMATED"
    ERROR = "ERROR"


class MaintenanceSensorExceptionType(str, Enum):
    MISSING_FEED = "MISSING_FEED"
    STALE_READING = "STALE_READING"
    UNIT_MISMATCH = "UNIT_MISMATCH"
    INVALID_THRESHOLD_MAPPING = "INVALID_THRESHOLD_MAPPING"
    EXTERNAL_SYNC_FAILURE = "EXTERNAL_SYNC_FAILURE"


class MaintenanceSensorExceptionStatus(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    IGNORED = "IGNORED"


class MaintenanceTemplateStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    RETIRED = "RETIRED"


class MaintenancePlanStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    RETIRED = "RETIRED"


class MaintenancePlanType(str, Enum):
    PREVENTIVE = "PREVENTIVE"
    INSPECTION = "INSPECTION"
    LUBRICATION = "LUBRICATION"
    CALIBRATION = "CALIBRATION"
    CONDITION_BASED = "CONDITION_BASED"


class MaintenanceCalendarFrequencyUnit(str, Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY = "YEARLY"
    CUSTOM_DAYS = "CUSTOM_DAYS"


class MaintenanceSensorDirection(str, Enum):
    GREATER_OR_EQUAL = "GREATER_OR_EQUAL"
    LESS_OR_EQUAL = "LESS_OR_EQUAL"
    EQUAL = "EQUAL"


class MaintenancePlanTaskTriggerScope(str, Enum):
    INHERIT_PLAN = "INHERIT_PLAN"
    TASK_OVERRIDE = "TASK_OVERRIDE"


class MaintenanceFailureCodeType(str, Enum):
    SYMPTOM = "SYMPTOM"
    CAUSE = "CAUSE"
    REMEDY = "REMEDY"


class MaintenanceSchedulePolicy(str, Enum):
    FIXED = "FIXED"
    FLOATING = "FLOATING"


class MaintenanceGenerationLeadUnit(str, Enum):
    DAYS = "DAYS"
    WEEKS = "WEEKS"
    MONTHS = "MONTHS"


class MaintenancePreventiveInstanceStatus(str, Enum):
    PLANNED = "PLANNED"
    GENERATED = "GENERATED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


__all__ = [
    "MaintenanceCalendarFrequencyUnit",
    "MaintenanceCriticality",
    "MaintenanceFailureCodeType",
    "MaintenanceGenerationLeadUnit",
    "MaintenanceLifecycleStatus",
    "MaintenanceMaterialProcurementStatus",
    "MaintenancePlanStatus",
    "MaintenancePlanTaskTriggerScope",
    "MaintenancePlanType",
    "MaintenancePreventiveInstanceStatus",
    "MaintenancePriority",
    "MaintenanceSchedulePolicy",
    "MaintenanceSensorDirection",
    "MaintenanceSensorExceptionStatus",
    "MaintenanceSensorExceptionType",
    "MaintenanceSensorQualityState",
    "MaintenanceTaskCompletionRule",
    "MaintenanceTemplateStatus",
    "MaintenanceTriggerMode",
    "MaintenanceWorkOrderStatus",
    "MaintenanceWorkOrderTaskStatus",
    "MaintenanceWorkOrderTaskStepStatus",
    "MaintenanceWorkOrderType",
    "MaintenanceWorkRequestSourceType",
    "MaintenanceWorkRequestStatus",
]
