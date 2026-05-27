from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

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
from src.core.platform.common.ids import generate_id


@dataclass
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

    @staticmethod
    def create(
        *,
        organization_id: str,
        task_template_code: str,
        name: str,
        description: str = "",
        maintenance_type: str = "",
        revision_no: int = 1,
        template_status: MaintenanceTemplateStatus = MaintenanceTemplateStatus.DRAFT,
        estimated_minutes: int | None = None,
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


@dataclass
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

    @staticmethod
    def create(
        *,
        organization_id: str,
        task_template_id: str,
        step_number: int,
        instruction: str,
        expected_result: str = "",
        hint_level: str = "",
        hint_text: str = "",
        requires_confirmation: bool = False,
        requires_measurement: bool = False,
        requires_photo: bool = False,
        measurement_unit: str = "",
        sort_order: int = 0,
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


@dataclass
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

    @staticmethod
    def create(
        *,
        organization_id: str,
        plan_id: str,
        due_at: datetime,
        due_counter: Decimal | None = None,
        status: MaintenancePreventiveInstanceStatus = MaintenancePreventiveInstanceStatus.PLANNED,
        generated_at: datetime | None = None,
        generated_work_request_id: str | None = None,
        generated_work_order_id: str | None = None,
        completed_at: datetime | None = None,
        notes: str = "",
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
            created_at=now,
            updated_at=now,
            version=1,
        )


@dataclass
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
        status: MaintenancePlanStatus = MaintenancePlanStatus.DRAFT,
        plan_type: MaintenancePlanType = MaintenancePlanType.PREVENTIVE,
        priority: MaintenancePriority = MaintenancePriority.MEDIUM,
        trigger_mode: MaintenanceTriggerMode = MaintenanceTriggerMode.CALENDAR,
        schedule_policy: MaintenanceSchedulePolicy = MaintenanceSchedulePolicy.FIXED,
        calendar_frequency_unit: MaintenanceCalendarFrequencyUnit | None = None,
        calendar_frequency_value: int | None = None,
        generation_horizon_count: int = 13,
        generation_lead_value: int = 0,
        generation_lead_unit: MaintenanceGenerationLeadUnit = MaintenanceGenerationLeadUnit.DAYS,
        sensor_id: str | None = None,
        sensor_threshold: Decimal | None = None,
        sensor_direction: MaintenanceSensorDirection | None = None,
        sensor_reset_rule: str = "",
        last_generated_at: datetime | None = None,
        last_completed_at: datetime | None = None,
        next_due_at: datetime | None = None,
        next_due_counter: Decimal | None = None,
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


@dataclass
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

    @staticmethod
    def create(
        *,
        organization_id: str,
        plan_id: str,
        task_template_id: str,
        trigger_scope: MaintenancePlanTaskTriggerScope = MaintenancePlanTaskTriggerScope.INHERIT_PLAN,
        trigger_mode_override: MaintenanceTriggerMode | None = None,
        calendar_frequency_unit_override: MaintenanceCalendarFrequencyUnit | None = None,
        calendar_frequency_value_override: int | None = None,
        sensor_id_override: str | None = None,
        sensor_threshold_override: Decimal | None = None,
        sensor_direction_override: MaintenanceSensorDirection | None = None,
        sequence_no: int = 1,
        is_mandatory: bool = True,
        default_assigned_employee_id: str | None = None,
        default_assigned_team_id: str | None = None,
        estimated_minutes_override: int | None = None,
        last_generated_at: datetime | None = None,
        next_due_at: datetime | None = None,
        next_due_counter: Decimal | None = None,
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
    "MaintenancePreventivePlan",
    "MaintenancePreventivePlanInstance",
    "MaintenancePreventivePlanTask",
    "MaintenanceTaskStepTemplate",
    "MaintenanceTaskTemplate",
]
