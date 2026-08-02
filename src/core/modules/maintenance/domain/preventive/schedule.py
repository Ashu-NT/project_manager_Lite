from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from pydantic import field_validator, model_validator

from src.core.modules.maintenance.domain._validation import (
    normalize_calendar_frequency_unit,
    normalize_generation_lead_unit,
    normalize_optional_date,
    normalize_optional_datetime,
    normalize_optional_decimal_value,
    normalize_optional_identifier,
    normalize_optional_non_negative_int,
    normalize_optional_text,
    normalize_optional_upper_text,
    normalize_plan_status,
    normalize_plan_task_trigger_scope,
    normalize_plan_type,
    normalize_positive_int,
    normalize_preventive_instance_status,
    normalize_priority,
    normalize_required_text,
    normalize_schedule_policy,
    normalize_sensor_direction,
    normalize_template_status,
    normalize_trigger_mode,
    normalize_maintenance_code,
    normalize_maintenance_name,
)
from src.core.modules.maintenance.domain.enums import (
    MaintenanceCalendarFrequencyUnit,
    MaintenanceGenerationLeadUnit,
    MaintenancePlanStatus,
    MaintenancePlanTaskTriggerScope,
    MaintenancePlanType,
    MaintenancePreventiveInstanceStatus,
    MaintenancePriority,
    MaintenanceSchedulePolicy,
    MaintenanceSensorDirection,
    MaintenanceTemplateStatus,
    MaintenanceTriggerMode,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.ids import generate_id
from src.core.platform.common.pydantic import validated_dataclass


@validated_dataclass
class MaintenanceTaskTemplate:
    id: str
    organization_id: str
    task_template_code: str
    name: str
    description: str = ""
    maintenance_type: str = ""
    revision_no: int = 1
    template_status: MaintenanceTemplateStatus = MaintenanceTemplateStatus.DRAFT
    estimated_minutes: int | None = None
    required_skill: str = ""
    requires_shutdown: bool = False
    requires_permit: bool = False
    is_active: bool = True
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @field_validator("id", "organization_id", mode="before")
    @classmethod
    def _validate_required_ids(cls, value: object, info) -> str:
        messages = {
            "id": (
                "Maintenance task template ID is required.",
                "MAINTENANCE_TASK_TEMPLATE_ID_REQUIRED",
            ),
            "organization_id": (
                "Organization ID is required.",
                "MAINTENANCE_TASK_TEMPLATE_ORGANIZATION_REQUIRED",
            ),
        }
        message, code = messages[info.field_name]
        return normalize_required_text(value, message=message, code=code)

    @field_validator("task_template_code", mode="before")
    @classmethod
    def _validate_code(cls, value: object) -> str:
        return normalize_maintenance_code(value, label="Task template code")

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: object) -> str:
        return normalize_maintenance_name(value, label="Task template name")

    @field_validator("description", "required_skill", "notes", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("maintenance_type", mode="before")
    @classmethod
    def _normalize_maintenance_type(cls, value: object) -> str:
        return normalize_optional_upper_text(value)

    @field_validator("revision_no", mode="before")
    @classmethod
    def _validate_revision_no(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Revision number must be greater than zero.",
            code="REVISION_NUMBER_INVALID",
        )

    @field_validator("template_status", mode="before")
    @classmethod
    def _validate_template_status(cls, value: object) -> MaintenanceTemplateStatus:
        return normalize_template_status(value)

    @field_validator("estimated_minutes", mode="before")
    @classmethod
    def _validate_estimated_minutes(cls, value: object) -> int | None:
        return normalize_optional_non_negative_int(value, label="Estimated minutes")

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime | None:
        return normalize_optional_datetime(
            value,
            message=f"Maintenance task template {info.field_name.replace('_', ' ')} is invalid.",
            code=f"MAINTENANCE_TASK_TEMPLATE_{info.field_name.upper()}_INVALID",
        )

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Maintenance task template version must be positive.",
            code="MAINTENANCE_TASK_TEMPLATE_VERSION_INVALID",
        )

    @model_validator(mode="after")
    def _validate_ranges(self) -> "MaintenanceTaskTemplate":
        if (
            self.updated_at is not None
            and self.created_at is not None
            and self.updated_at < self.created_at
        ):
            raise ValidationError(
                "Updated timestamp cannot be earlier than created timestamp.",
                code="MAINTENANCE_TASK_TEMPLATE_UPDATED_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        *,
        organization_id: str,
        task_template_code: str,
        name: str,
        description: str = "",
        maintenance_type: str = "",
        revision_no: int | str = 1,
        template_status: MaintenanceTemplateStatus | str | None = MaintenanceTemplateStatus.DRAFT,
        estimated_minutes: int | str | None = None,
        required_skill: str = "",
        requires_shutdown: bool = False,
        requires_permit: bool = False,
        is_active: bool = True,
        notes: str = "",
    ) -> "MaintenanceTaskTemplate":
        now = datetime.now(timezone.utc)
        return MaintenanceTaskTemplate(
            id=generate_id(),
            organization_id=organization_id,
            task_template_code=task_template_code,
            name=name,
            description=description,
            maintenance_type=maintenance_type,
            revision_no=revision_no,
            template_status=template_status,
            estimated_minutes=estimated_minutes,
            required_skill=required_skill,
            requires_shutdown=requires_shutdown,
            requires_permit=requires_permit,
            is_active=is_active,
            notes=notes,
            created_at=now,
            updated_at=now,
            version=1,
        )


@validated_dataclass
class MaintenanceTaskStepTemplate:
    id: str
    organization_id: str
    task_template_id: str
    step_number: int
    instruction: str
    expected_result: str = ""
    hint_level: str = ""
    hint_text: str = ""
    requires_confirmation: bool = False
    requires_measurement: bool = False
    requires_photo: bool = False
    measurement_unit: str = ""
    sort_order: int = 0
    is_active: bool = True
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @field_validator("id", "organization_id", "task_template_id", mode="before")
    @classmethod
    def _validate_required_ids(cls, value: object, info) -> str:
        messages = {
            "id": (
                "Maintenance task step template ID is required.",
                "MAINTENANCE_TASK_STEP_TEMPLATE_ID_REQUIRED",
            ),
            "organization_id": (
                "Organization ID is required.",
                "MAINTENANCE_TASK_STEP_TEMPLATE_ORGANIZATION_REQUIRED",
            ),
            "task_template_id": (
                "Task template ID is required.",
                "MAINTENANCE_TASK_STEP_TEMPLATE_TASK_TEMPLATE_REQUIRED",
            ),
        }
        message, code = messages[info.field_name]
        return normalize_required_text(value, message=message, code=code)

    @field_validator("step_number", mode="before")
    @classmethod
    def _validate_step_number(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Step number must be greater than zero.",
            code="STEP_NUMBER_INVALID",
        )

    @field_validator("instruction", mode="before")
    @classmethod
    def _validate_instruction(cls, value: object) -> str:
        return normalize_maintenance_name(value, label="Instruction")

    @field_validator("expected_result", "hint_text", "notes", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("hint_level", "measurement_unit", mode="before")
    @classmethod
    def _normalize_upper_text_fields(cls, value: object) -> str:
        return normalize_optional_upper_text(value)

    @field_validator("sort_order", mode="before")
    @classmethod
    def _validate_sort_order(cls, value: object) -> int:
        resolved = normalize_optional_non_negative_int(value, label="Sort order")
        return 0 if resolved is None else resolved

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime | None:
        return normalize_optional_datetime(
            value,
            message=f"Maintenance task step template {info.field_name.replace('_', ' ')} is invalid.",
            code=f"MAINTENANCE_TASK_STEP_TEMPLATE_{info.field_name.upper()}_INVALID",
        )

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Maintenance task step template version must be positive.",
            code="MAINTENANCE_TASK_STEP_TEMPLATE_VERSION_INVALID",
        )

    @model_validator(mode="after")
    def _validate_ranges(self) -> "MaintenanceTaskStepTemplate":
        if (
            self.updated_at is not None
            and self.created_at is not None
            and self.updated_at < self.created_at
        ):
            raise ValidationError(
                "Updated timestamp cannot be earlier than created timestamp.",
                code="MAINTENANCE_TASK_STEP_TEMPLATE_UPDATED_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        *,
        organization_id: str,
        task_template_id: str,
        step_number: int | str,
        instruction: str,
        expected_result: str = "",
        hint_level: str = "",
        hint_text: str = "",
        requires_confirmation: bool = False,
        requires_measurement: bool = False,
        requires_photo: bool = False,
        measurement_unit: str = "",
        sort_order: int | str | None = 0,
        is_active: bool = True,
        notes: str = "",
    ) -> "MaintenanceTaskStepTemplate":
        now = datetime.now(timezone.utc)
        return MaintenanceTaskStepTemplate(
            id=generate_id(),
            organization_id=organization_id,
            task_template_id=task_template_id,
            step_number=step_number,
            instruction=instruction,
            expected_result=expected_result,
            hint_level=hint_level,
            hint_text=hint_text,
            requires_confirmation=requires_confirmation,
            requires_measurement=requires_measurement,
            requires_photo=requires_photo,
            measurement_unit=measurement_unit,
            sort_order=sort_order,
            is_active=is_active,
            notes=notes,
            created_at=now,
            updated_at=now,
            version=1,
        )


@validated_dataclass
class MaintenancePreventivePlanInstance:
    id: str
    organization_id: str
    plan_id: str
    due_at: datetime
    due_counter: Decimal | None = None
    status: MaintenancePreventiveInstanceStatus = MaintenancePreventiveInstanceStatus.PLANNED
    generated_at: datetime | None = None
    generated_work_request_id: str | None = None
    generated_work_order_id: str | None = None
    completed_at: datetime | None = None
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @field_validator("id", "organization_id", "plan_id", mode="before")
    @classmethod
    def _validate_required_ids(cls, value: object, info) -> str:
        messages = {
            "id": (
                "Maintenance preventive plan instance ID is required.",
                "MAINTENANCE_PREVENTIVE_PLAN_INSTANCE_ID_REQUIRED",
            ),
            "organization_id": (
                "Organization ID is required.",
                "MAINTENANCE_PREVENTIVE_PLAN_INSTANCE_ORGANIZATION_REQUIRED",
            ),
            "plan_id": (
                "Preventive plan ID is required.",
                "MAINTENANCE_PREVENTIVE_PLAN_INSTANCE_PLAN_REQUIRED",
            ),
        }
        message, code = messages[info.field_name]
        return normalize_required_text(value, message=message, code=code)

    @field_validator("due_at", mode="before")
    @classmethod
    def _validate_due_at(cls, value: object) -> datetime:
        resolved = normalize_optional_datetime(
            value,
            message="Maintenance preventive plan instance due at is invalid.",
            code="MAINTENANCE_PREVENTIVE_PLAN_INSTANCE_DUE_AT_INVALID",
        )
        if resolved is None:
            raise ValidationError(
                "Preventive plan instance due at is required.",
                code="MAINTENANCE_PREVENTIVE_PLAN_INSTANCE_DUE_AT_REQUIRED",
            )
        return resolved

    @field_validator("due_counter", mode="before")
    @classmethod
    def _validate_due_counter(cls, value: object) -> Decimal | None:
        return normalize_optional_decimal_value(value, label="Due counter")

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, value: object) -> MaintenancePreventiveInstanceStatus:
        return normalize_preventive_instance_status(value)

    @field_validator(
        "generated_work_request_id",
        "generated_work_order_id",
        mode="before",
    )
    @classmethod
    def _normalize_optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("notes", mode="before")
    @classmethod
    def _normalize_notes(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("generated_at", "completed_at", "created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime | None:
        return normalize_optional_datetime(
            value,
            message=f"Maintenance preventive plan instance {info.field_name.replace('_', ' ')} is invalid.",
            code=f"MAINTENANCE_PREVENTIVE_PLAN_INSTANCE_{info.field_name.upper()}_INVALID",
        )

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Maintenance preventive plan instance version must be positive.",
            code="MAINTENANCE_PREVENTIVE_PLAN_INSTANCE_VERSION_INVALID",
        )

    @model_validator(mode="after")
    def _validate_ranges(self) -> "MaintenancePreventivePlanInstance":
        if (
            self.completed_at is not None
            and self.generated_at is not None
            and self.completed_at < self.generated_at
        ):
            raise ValidationError(
                "Completed timestamp cannot be earlier than generated timestamp.",
                code="MAINTENANCE_PREVENTIVE_PLAN_INSTANCE_COMPLETED_RANGE_INVALID",
            )
        if (
            self.updated_at is not None
            and self.created_at is not None
            and self.updated_at < self.created_at
        ):
            raise ValidationError(
                "Updated timestamp cannot be earlier than created timestamp.",
                code="MAINTENANCE_PREVENTIVE_PLAN_INSTANCE_UPDATED_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        *,
        organization_id: str,
        plan_id: str,
        due_at: datetime | str,
        due_counter: Decimal | int | float | str | None = None,
        status: MaintenancePreventiveInstanceStatus | str | None = MaintenancePreventiveInstanceStatus.PLANNED,
        generated_at: datetime | str | None = None,
        generated_work_request_id: str | None = None,
        generated_work_order_id: str | None = None,
        completed_at: datetime | str | None = None,
        notes: str = "",
        created_at: datetime | str | None = None,
        updated_at: datetime | str | None = None,
    ) -> "MaintenancePreventivePlanInstance":
        now = datetime.now(timezone.utc)
        return MaintenancePreventivePlanInstance(
            id=generate_id(),
            organization_id=organization_id,
            plan_id=plan_id,
            due_at=due_at,
            due_counter=due_counter,
            status=status,
            generated_at=generated_at,
            generated_work_request_id=generated_work_request_id,
            generated_work_order_id=generated_work_order_id,
            completed_at=completed_at,
            notes=notes,
            created_at=now if created_at is None else created_at,
            updated_at=now if updated_at is None else updated_at,
            version=1,
        )


@validated_dataclass
class MaintenanceBlackoutWindow:
    id: str
    organization_id: str
    preventive_plan_id: str
    name: str
    start_date: date
    end_date: date
    recurrence: str = "NONE"
    notes: str = ""
    is_active: bool = True
    version: int = 1

    @field_validator("id", "organization_id", "preventive_plan_id", mode="before")
    @classmethod
    def _validate_required_ids(cls, value: object, info) -> str:
        messages = {
            "id": (
                "Maintenance blackout window ID is required.",
                "MAINTENANCE_BLACKOUT_WINDOW_ID_REQUIRED",
            ),
            "organization_id": (
                "Organization ID is required.",
                "MAINTENANCE_BLACKOUT_WINDOW_ORGANIZATION_REQUIRED",
            ),
            "preventive_plan_id": (
                "Preventive plan ID is required.",
                "MAINTENANCE_BLACKOUT_WINDOW_PLAN_REQUIRED",
            ),
        }
        message, code = messages[info.field_name]
        return normalize_required_text(value, message=message, code=code)

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: object) -> str:
        return normalize_maintenance_name(value, label="Blackout window name")

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def _validate_dates(cls, value: object, info) -> date:
        resolved = normalize_optional_date(
            value,
            label=info.field_name.replace("_", " ").title(),
        )
        if resolved is None:
            raise ValidationError(
                f"{info.field_name.replace('_', ' ').title()} is required.",
                code=f"MAINTENANCE_BLACKOUT_WINDOW_{info.field_name.upper()}_REQUIRED",
            )
        return resolved

    @field_validator("recurrence", mode="before")
    @classmethod
    def _validate_recurrence(cls, value: object) -> str:
        normalized = normalize_optional_upper_text(value) or "NONE"
        if normalized not in {"NONE", "ANNUAL"}:
            raise ValidationError(
                "Maintenance blackout window recurrence is invalid.",
                code="MAINTENANCE_BLACKOUT_WINDOW_RECURRENCE_INVALID",
            )
        return normalized

    @field_validator("notes", mode="before")
    @classmethod
    def _normalize_notes(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Maintenance blackout window version must be positive.",
            code="MAINTENANCE_BLACKOUT_WINDOW_VERSION_INVALID",
        )

    @model_validator(mode="after")
    def _validate_ranges(self) -> "MaintenanceBlackoutWindow":
        if self.recurrence != "ANNUAL" and self.end_date < self.start_date:
            raise ValidationError(
                "Blackout window end date cannot be earlier than start date.",
                code="MAINTENANCE_BLACKOUT_WINDOW_DATE_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        *,
        organization_id: str,
        preventive_plan_id: str,
        name: str,
        start_date: date | str,
        end_date: date | str,
        recurrence: str = "NONE",
        notes: str = "",
    ) -> "MaintenanceBlackoutWindow":
        return MaintenanceBlackoutWindow(
            id=generate_id(),
            organization_id=organization_id,
            preventive_plan_id=preventive_plan_id,
            name=name,
            start_date=start_date,
            end_date=end_date,
            recurrence=recurrence,
            notes=notes,
        )

    def covers(self, check_date: date) -> bool:
        if not self.is_active:
            return False
        if self.recurrence == "ANNUAL":
            adjusted = self.start_date.replace(year=check_date.year)
            adjusted_end = self.end_date.replace(year=check_date.year)
            if adjusted_end < adjusted:
                adjusted_end = adjusted_end.replace(year=check_date.year + 1)
            return adjusted <= check_date <= adjusted_end
        return self.start_date <= check_date <= self.end_date


@validated_dataclass
class MaintenancePreventivePlan:
    id: str
    organization_id: str
    site_id: str
    plan_code: str
    name: str
    asset_id: str | None = None
    component_id: str | None = None
    system_id: str | None = None
    description: str = ""
    status: MaintenancePlanStatus = MaintenancePlanStatus.DRAFT
    plan_type: MaintenancePlanType = MaintenancePlanType.PREVENTIVE
    priority: MaintenancePriority = MaintenancePriority.MEDIUM
    trigger_mode: MaintenanceTriggerMode = MaintenanceTriggerMode.CALENDAR
    schedule_policy: MaintenanceSchedulePolicy = MaintenanceSchedulePolicy.FIXED
    calendar_frequency_unit: MaintenanceCalendarFrequencyUnit | None = None
    calendar_frequency_value: int | None = None
    generation_horizon_count: int = 13
    generation_lead_value: int = 0
    generation_lead_unit: MaintenanceGenerationLeadUnit = MaintenanceGenerationLeadUnit.DAYS
    sensor_id: str | None = None
    sensor_threshold: Decimal | None = None
    sensor_direction: MaintenanceSensorDirection | None = None
    sensor_reset_rule: str = ""
    last_generated_at: datetime | None = None
    last_completed_at: datetime | None = None
    next_due_at: datetime | None = None
    next_due_counter: Decimal | None = None
    requires_shutdown: bool = False
    approval_required: bool = False
    auto_generate_work_order: bool = False
    is_active: bool = True
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @field_validator("id", "organization_id", "site_id", mode="before")
    @classmethod
    def _validate_required_ids(cls, value: object, info) -> str:
        messages = {
            "id": (
                "Maintenance preventive plan ID is required.",
                "MAINTENANCE_PREVENTIVE_PLAN_ID_REQUIRED",
            ),
            "organization_id": (
                "Organization ID is required.",
                "MAINTENANCE_PREVENTIVE_PLAN_ORGANIZATION_REQUIRED",
            ),
            "site_id": (
                "Site ID is required.",
                "MAINTENANCE_PREVENTIVE_PLAN_SITE_REQUIRED",
            ),
        }
        message, code = messages[info.field_name]
        return normalize_required_text(value, message=message, code=code)

    @field_validator("plan_code", mode="before")
    @classmethod
    def _validate_plan_code(cls, value: object) -> str:
        return normalize_maintenance_code(value, label="Preventive plan code")

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: object) -> str:
        return normalize_maintenance_name(value, label="Preventive plan name")

    @field_validator("asset_id", "component_id", "system_id", "sensor_id", mode="before")
    @classmethod
    def _normalize_optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("description", "sensor_reset_rule", "notes", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, value: object) -> MaintenancePlanStatus:
        return normalize_plan_status(value)

    @field_validator("plan_type", mode="before")
    @classmethod
    def _validate_plan_type(cls, value: object) -> MaintenancePlanType:
        return normalize_plan_type(value)

    @field_validator("priority", mode="before")
    @classmethod
    def _validate_priority(cls, value: object) -> MaintenancePriority:
        return normalize_priority(value)

    @field_validator("trigger_mode", mode="before")
    @classmethod
    def _validate_trigger_mode(cls, value: object) -> MaintenanceTriggerMode:
        return normalize_trigger_mode(value)

    @field_validator("schedule_policy", mode="before")
    @classmethod
    def _validate_schedule_policy(cls, value: object) -> MaintenanceSchedulePolicy:
        return normalize_schedule_policy(value)

    @field_validator("calendar_frequency_unit", mode="before")
    @classmethod
    def _validate_calendar_frequency_unit(
        cls,
        value: object,
    ) -> MaintenanceCalendarFrequencyUnit | None:
        return normalize_calendar_frequency_unit(value)

    @field_validator("calendar_frequency_value", mode="before")
    @classmethod
    def _validate_calendar_frequency_value(cls, value: object) -> int | None:
        return normalize_optional_non_negative_int(value, label="Calendar frequency value")

    @field_validator("generation_horizon_count", mode="before")
    @classmethod
    def _validate_generation_horizon_count(cls, value: object) -> int:
        resolved = normalize_optional_non_negative_int(value, label="Generation horizon count")
        return resolved if resolved not in (None, 0) else 13

    @field_validator("generation_lead_value", mode="before")
    @classmethod
    def _validate_generation_lead_value(cls, value: object) -> int:
        resolved = normalize_optional_non_negative_int(value, label="Generation lead value")
        return 0 if resolved is None else resolved

    @field_validator("generation_lead_unit", mode="before")
    @classmethod
    def _validate_generation_lead_unit(cls, value: object) -> MaintenanceGenerationLeadUnit:
        return normalize_generation_lead_unit(value)

    @field_validator("sensor_threshold", "next_due_counter", mode="before")
    @classmethod
    def _validate_optional_decimals(cls, value: object, info) -> Decimal | None:
        labels = {
            "sensor_threshold": "Sensor threshold",
            "next_due_counter": "Next due counter",
        }
        return normalize_optional_decimal_value(value, label=labels[info.field_name])

    @field_validator("sensor_direction", mode="before")
    @classmethod
    def _validate_sensor_direction(
        cls,
        value: object,
    ) -> MaintenanceSensorDirection | None:
        return normalize_sensor_direction(value)

    @field_validator(
        "last_generated_at",
        "last_completed_at",
        "next_due_at",
        "created_at",
        "updated_at",
        mode="before",
    )
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime | None:
        return normalize_optional_datetime(
            value,
            message=f"Maintenance preventive plan {info.field_name.replace('_', ' ')} is invalid.",
            code=f"MAINTENANCE_PREVENTIVE_PLAN_{info.field_name.upper()}_INVALID",
        )

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Maintenance preventive plan version must be positive.",
            code="MAINTENANCE_PREVENTIVE_PLAN_VERSION_INVALID",
        )

    @model_validator(mode="after")
    def _validate_ranges(self) -> "MaintenancePreventivePlan":
        if (
            self.updated_at is not None
            and self.created_at is not None
            and self.updated_at < self.created_at
        ):
            raise ValidationError(
                "Updated timestamp cannot be earlier than created timestamp.",
                code="MAINTENANCE_PREVENTIVE_PLAN_UPDATED_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        *,
        organization_id: str,
        site_id: str,
        plan_code: str,
        name: str,
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        description: str = "",
        status: MaintenancePlanStatus | str | None = MaintenancePlanStatus.DRAFT,
        plan_type: MaintenancePlanType | str | None = MaintenancePlanType.PREVENTIVE,
        priority: MaintenancePriority | str | None = MaintenancePriority.MEDIUM,
        trigger_mode: MaintenanceTriggerMode | str | None = MaintenanceTriggerMode.CALENDAR,
        schedule_policy: MaintenanceSchedulePolicy | str | None = MaintenanceSchedulePolicy.FIXED,
        calendar_frequency_unit: MaintenanceCalendarFrequencyUnit | str | None = None,
        calendar_frequency_value: int | str | None = None,
        generation_horizon_count: int | str | None = 13,
        generation_lead_value: int | str | None = 0,
        generation_lead_unit: MaintenanceGenerationLeadUnit | str | None = MaintenanceGenerationLeadUnit.DAYS,
        sensor_id: str | None = None,
        sensor_threshold: Decimal | int | float | str | None = None,
        sensor_direction: MaintenanceSensorDirection | str | None = None,
        sensor_reset_rule: str = "",
        last_generated_at: datetime | str | None = None,
        last_completed_at: datetime | str | None = None,
        next_due_at: datetime | str | None = None,
        next_due_counter: Decimal | int | float | str | None = None,
        requires_shutdown: bool = False,
        approval_required: bool = False,
        auto_generate_work_order: bool = False,
        is_active: bool = True,
        notes: str = "",
    ) -> "MaintenancePreventivePlan":
        now = datetime.now(timezone.utc)
        return MaintenancePreventivePlan(
            id=generate_id(),
            organization_id=organization_id,
            site_id=site_id,
            plan_code=plan_code,
            name=name,
            asset_id=asset_id,
            component_id=component_id,
            system_id=system_id,
            description=description,
            status=status,
            plan_type=plan_type,
            priority=priority,
            trigger_mode=trigger_mode,
            schedule_policy=schedule_policy,
            calendar_frequency_unit=calendar_frequency_unit,
            calendar_frequency_value=calendar_frequency_value,
            generation_horizon_count=generation_horizon_count,
            generation_lead_value=generation_lead_value,
            generation_lead_unit=generation_lead_unit,
            sensor_id=sensor_id,
            sensor_threshold=sensor_threshold,
            sensor_direction=sensor_direction,
            sensor_reset_rule=sensor_reset_rule,
            last_generated_at=last_generated_at,
            last_completed_at=last_completed_at,
            next_due_at=next_due_at,
            next_due_counter=next_due_counter,
            requires_shutdown=requires_shutdown,
            approval_required=approval_required,
            auto_generate_work_order=auto_generate_work_order,
            is_active=is_active,
            notes=notes,
            created_at=now,
            updated_at=now,
            version=1,
        )


@validated_dataclass
class MaintenancePreventivePlanTask:
    id: str
    organization_id: str
    plan_id: str
    task_template_id: str
    trigger_scope: MaintenancePlanTaskTriggerScope = MaintenancePlanTaskTriggerScope.INHERIT_PLAN
    trigger_mode_override: MaintenanceTriggerMode | None = None
    calendar_frequency_unit_override: MaintenanceCalendarFrequencyUnit | None = None
    calendar_frequency_value_override: int | None = None
    sensor_id_override: str | None = None
    sensor_threshold_override: Decimal | None = None
    sensor_direction_override: MaintenanceSensorDirection | None = None
    sequence_no: int = 1
    is_mandatory: bool = True
    default_assigned_employee_id: str | None = None
    default_assigned_team_id: str | None = None
    estimated_minutes_override: int | None = None
    last_generated_at: datetime | None = None
    next_due_at: datetime | None = None
    next_due_counter: Decimal | None = None
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @field_validator("id", "organization_id", "plan_id", "task_template_id", mode="before")
    @classmethod
    def _validate_required_ids(cls, value: object, info) -> str:
        messages = {
            "id": (
                "Maintenance preventive plan task ID is required.",
                "MAINTENANCE_PREVENTIVE_PLAN_TASK_ID_REQUIRED",
            ),
            "organization_id": (
                "Organization ID is required.",
                "MAINTENANCE_PREVENTIVE_PLAN_TASK_ORGANIZATION_REQUIRED",
            ),
            "plan_id": (
                "Preventive plan ID is required.",
                "MAINTENANCE_PREVENTIVE_PLAN_TASK_PLAN_REQUIRED",
            ),
            "task_template_id": (
                "Task template ID is required.",
                "MAINTENANCE_PREVENTIVE_PLAN_TASK_TEMPLATE_REQUIRED",
            ),
        }
        message, code = messages[info.field_name]
        return normalize_required_text(value, message=message, code=code)

    @field_validator("trigger_scope", mode="before")
    @classmethod
    def _validate_trigger_scope(cls, value: object) -> MaintenancePlanTaskTriggerScope:
        return normalize_plan_task_trigger_scope(value)

    @field_validator("trigger_mode_override", mode="before")
    @classmethod
    def _validate_trigger_mode_override(
        cls,
        value: object,
    ) -> MaintenanceTriggerMode | None:
        if value in (None, ""):
            return None
        return normalize_trigger_mode(value)

    @field_validator("calendar_frequency_unit_override", mode="before")
    @classmethod
    def _validate_calendar_frequency_unit_override(
        cls,
        value: object,
    ) -> MaintenanceCalendarFrequencyUnit | None:
        return normalize_calendar_frequency_unit(value)

    @field_validator("calendar_frequency_value_override", "estimated_minutes_override", mode="before")
    @classmethod
    def _validate_optional_ints(cls, value: object, info) -> int | None:
        labels = {
            "calendar_frequency_value_override": "Calendar frequency value override",
            "estimated_minutes_override": "Estimated minutes override",
        }
        return normalize_optional_non_negative_int(value, label=labels[info.field_name])

    @field_validator(
        "sensor_id_override",
        "default_assigned_employee_id",
        "default_assigned_team_id",
        mode="before",
    )
    @classmethod
    def _normalize_optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("sensor_threshold_override", "next_due_counter", mode="before")
    @classmethod
    def _validate_optional_decimals(cls, value: object, info) -> Decimal | None:
        labels = {
            "sensor_threshold_override": "Sensor threshold override",
            "next_due_counter": "Next due counter",
        }
        return normalize_optional_decimal_value(value, label=labels[info.field_name])

    @field_validator("sensor_direction_override", mode="before")
    @classmethod
    def _validate_sensor_direction_override(
        cls,
        value: object,
    ) -> MaintenanceSensorDirection | None:
        return normalize_sensor_direction(value)

    @field_validator("sequence_no", mode="before")
    @classmethod
    def _validate_sequence_no(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Sequence number must be greater than zero.",
            code="MAINTENANCE_PREVENTIVE_PLAN_TASK_SEQUENCE_INVALID",
        )

    @field_validator("notes", mode="before")
    @classmethod
    def _normalize_notes(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("last_generated_at", "next_due_at", "created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime | None:
        return normalize_optional_datetime(
            value,
            message=f"Maintenance preventive plan task {info.field_name.replace('_', ' ')} is invalid.",
            code=f"MAINTENANCE_PREVENTIVE_PLAN_TASK_{info.field_name.upper()}_INVALID",
        )

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Maintenance preventive plan task version must be positive.",
            code="MAINTENANCE_PREVENTIVE_PLAN_TASK_VERSION_INVALID",
        )

    @model_validator(mode="after")
    def _validate_ranges(self) -> "MaintenancePreventivePlanTask":
        override_fields = (
            self.trigger_mode_override,
            self.calendar_frequency_unit_override,
            self.calendar_frequency_value_override,
            self.sensor_id_override,
            self.sensor_threshold_override,
            self.sensor_direction_override,
        )
        if self.trigger_scope == MaintenancePlanTaskTriggerScope.INHERIT_PLAN:
            if any(value is not None for value in override_fields):
                raise ValidationError(
                    "Plan-task trigger overrides are only allowed when trigger scope is TASK_OVERRIDE.",
                    code="MAINTENANCE_PREVENTIVE_PLAN_TASK_OVERRIDE_NOT_ALLOWED",
                )
        elif self.trigger_mode_override is None:
            object.__setattr__(
                self,
                "trigger_mode_override",
                MaintenanceTriggerMode.CALENDAR,
            )
        if (
            self.updated_at is not None
            and self.created_at is not None
            and self.updated_at < self.created_at
        ):
            raise ValidationError(
                "Updated timestamp cannot be earlier than created timestamp.",
                code="MAINTENANCE_PREVENTIVE_PLAN_TASK_UPDATED_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        *,
        organization_id: str,
        plan_id: str,
        task_template_id: str,
        trigger_scope: MaintenancePlanTaskTriggerScope | str | None = MaintenancePlanTaskTriggerScope.INHERIT_PLAN,
        trigger_mode_override: MaintenanceTriggerMode | str | None = None,
        calendar_frequency_unit_override: MaintenanceCalendarFrequencyUnit | str | None = None,
        calendar_frequency_value_override: int | str | None = None,
        sensor_id_override: str | None = None,
        sensor_threshold_override: Decimal | int | float | str | None = None,
        sensor_direction_override: MaintenanceSensorDirection | str | None = None,
        sequence_no: int | str = 1,
        is_mandatory: bool = True,
        default_assigned_employee_id: str | None = None,
        default_assigned_team_id: str | None = None,
        estimated_minutes_override: int | str | None = None,
        last_generated_at: datetime | str | None = None,
        next_due_at: datetime | str | None = None,
        next_due_counter: Decimal | int | float | str | None = None,
        notes: str = "",
    ) -> "MaintenancePreventivePlanTask":
        now = datetime.now(timezone.utc)
        return MaintenancePreventivePlanTask(
            id=generate_id(),
            organization_id=organization_id,
            plan_id=plan_id,
            task_template_id=task_template_id,
            trigger_scope=trigger_scope,
            trigger_mode_override=trigger_mode_override,
            calendar_frequency_unit_override=calendar_frequency_unit_override,
            calendar_frequency_value_override=calendar_frequency_value_override,
            sensor_id_override=sensor_id_override,
            sensor_threshold_override=sensor_threshold_override,
            sensor_direction_override=sensor_direction_override,
            sequence_no=sequence_no,
            is_mandatory=is_mandatory,
            default_assigned_employee_id=default_assigned_employee_id,
            default_assigned_team_id=default_assigned_team_id,
            estimated_minutes_override=estimated_minutes_override,
            last_generated_at=last_generated_at,
            next_due_at=next_due_at,
            next_due_counter=next_due_counter,
            notes=notes,
            created_at=now,
            updated_at=now,
            version=1,
        )


__all__ = [
    "MaintenanceBlackoutWindow",
    "MaintenancePreventivePlan",
    "MaintenancePreventivePlanInstance",
    "MaintenancePreventivePlanTask",
    "MaintenanceTaskStepTemplate",
    "MaintenanceTaskTemplate",
]
