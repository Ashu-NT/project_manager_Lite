from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.maintenance.domain import (
    MaintenanceGenerationLeadUnit,
    MaintenancePlanTaskTriggerScope,
    MaintenancePlanType,
    MaintenancePriority,
    MaintenanceTemplateStatus,
    MaintenanceTriggerMode,
)


@dataclass(frozen=True)
class MaintenancePreventiveChoiceDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class MaintenancePreventiveQueueRowDescriptor:
    plan_id: str
    plan_code: str
    plan_label: str
    anchor_label: str
    plan_status: str
    plan_status_label: str
    due_state: str
    due_state_label: str
    due_reason: str
    generation_target: str
    generation_target_label: str
    trigger_label: str
    next_due_label: str
    is_due_soon: bool
    selected_plan_task_ids: tuple[str, ...]
    blocked_plan_task_ids: tuple[str, ...]
    version: int


@dataclass(frozen=True)
class MaintenancePreventiveForecastRowDescriptor:
    instance_id: str
    due_at_label: str
    generation_window_opens_at_label: str
    instance_status: str
    instance_status_label: str
    planner_state: str
    planner_state_label: str
    generated_work_request_id: str | None
    generated_work_order_id: str | None
    completed_at_label: str


@dataclass(frozen=True)
class MaintenancePreventiveGenerationResultDescriptor:
    plan_id: str
    plan_code: str
    generation_target: str
    generation_target_label: str
    generated_work_request_id: str | None
    generated_work_order_id: str | None
    generated_task_count: int
    generated_step_count: int
    skipped_reason: str


@dataclass(frozen=True)
class MaintenanceTaskTemplateDesktopDto:
    id: str
    task_template_code: str
    name: str
    description: str
    maintenance_type: str
    maintenance_type_label: str
    revision_no: int
    template_status: str
    template_status_label: str
    estimated_minutes: int | None
    required_skill: str
    requires_shutdown: bool
    requires_permit: bool
    is_active: bool
    active_label: str
    notes: str
    created_at: str
    updated_at: str
    version: int
    step_count: int


@dataclass(frozen=True)
class MaintenanceTaskStepTemplateDesktopDto:
    id: str
    task_template_id: str
    step_number: int
    sort_order: int
    instruction: str
    expected_result: str
    hint_level: str
    hint_level_label: str
    hint_text: str
    requires_confirmation: bool
    requires_measurement: bool
    requires_photo: bool
    measurement_unit: str
    is_active: bool
    active_label: str
    notes: str
    created_at: str
    updated_at: str
    version: int


@dataclass(frozen=True)
class MaintenancePreventivePlanDesktopDto:
    id: str
    site_id: str
    site_label: str
    plan_code: str
    name: str
    anchor_label: str
    asset_id: str | None
    asset_label: str
    component_id: str | None
    component_label: str
    system_id: str | None
    system_label: str
    description: str
    status: str
    status_label: str
    plan_type: str
    plan_type_label: str
    priority: str
    priority_label: str
    trigger_mode: str
    trigger_mode_label: str
    trigger_summary: str
    schedule_policy: str
    schedule_policy_label: str
    calendar_frequency_unit: str
    calendar_frequency_unit_label: str
    calendar_frequency_value: int | None
    generation_horizon_count: int
    generation_lead_value: int
    generation_lead_unit: str
    generation_lead_unit_label: str
    sensor_id: str | None
    sensor_label: str
    sensor_threshold: str
    sensor_direction: str
    sensor_direction_label: str
    sensor_reset_rule: str
    last_generated_at: str
    last_completed_at: str
    next_due_at: str
    next_due_label: str
    next_due_counter: str
    requires_shutdown: bool
    approval_required: bool
    auto_generate_work_order: bool
    is_active: bool
    active_label: str
    notes: str
    created_at: str
    updated_at: str
    version: int
    plan_task_count: int


@dataclass(frozen=True)
class MaintenancePreventivePlanTaskDesktopDto:
    id: str
    plan_id: str
    task_template_id: str
    task_template_label: str
    trigger_scope: str
    trigger_scope_label: str
    trigger_mode_override: str
    trigger_mode_override_label: str
    trigger_rule_summary: str
    sensor_id_override: str | None
    sensor_label_override: str
    sequence_no: int
    is_mandatory: bool
    default_assigned_team_id: str | None
    estimated_minutes_override: int | None
    last_generated_at: str
    next_due_at: str
    next_due_label: str
    next_due_counter: str
    notes: str
    version: int


@dataclass(frozen=True)
class MaintenanceTaskTemplateCreateCommand:
    task_template_code: str = ""
    name: str = ""
    description: str = ""
    maintenance_type: str = MaintenancePlanType.PREVENTIVE.value
    revision_no: int = 1
    template_status: str = MaintenanceTemplateStatus.DRAFT.value
    estimated_minutes: int | None = None
    required_skill: str = ""
    requires_shutdown: bool = False
    requires_permit: bool = False
    is_active: bool = True
    notes: str = ""


@dataclass(frozen=True)
class MaintenanceTaskTemplateUpdateCommand:
    task_template_id: str
    task_template_code: str | None = None
    name: str | None = None
    description: str | None = None
    maintenance_type: str | None = None
    revision_no: int | None = None
    template_status: str | None = None
    estimated_minutes: int | None = None
    required_skill: str | None = None
    requires_shutdown: bool | None = None
    requires_permit: bool | None = None
    is_active: bool | None = None
    notes: str | None = None
    expected_version: int | None = None


@dataclass(frozen=True)
class MaintenanceTaskStepTemplateCreateCommand:
    task_template_id: str
    step_number: int
    sort_order: int | None = None
    instruction: str = ""
    expected_result: str = ""
    hint_level: str = ""
    hint_text: str = ""
    requires_confirmation: bool = False
    requires_measurement: bool = False
    requires_photo: bool = False
    measurement_unit: str = ""
    is_active: bool = True
    notes: str = ""


@dataclass(frozen=True)
class MaintenanceTaskStepTemplateUpdateCommand:
    task_step_template_id: str
    step_number: int | None = None
    sort_order: int | None = None
    instruction: str | None = None
    expected_result: str | None = None
    hint_level: str | None = None
    hint_text: str | None = None
    requires_confirmation: bool | None = None
    requires_measurement: bool | None = None
    requires_photo: bool | None = None
    measurement_unit: str | None = None
    is_active: bool | None = None
    notes: str | None = None
    expected_version: int | None = None


@dataclass(frozen=True)
class MaintenancePreventivePlanCreateCommand:
    site_id: str
    plan_code: str = ""
    name: str = ""
    asset_id: str | None = None
    component_id: str | None = None
    system_id: str | None = None
    description: str = ""
    status: str = "ACTIVE"
    plan_type: str = MaintenancePlanType.PREVENTIVE.value
    priority: str = MaintenancePriority.MEDIUM.value
    trigger_mode: str = MaintenanceTriggerMode.CALENDAR.value
    schedule_policy: str = "FIXED"
    calendar_frequency_unit: str | None = None
    calendar_frequency_value: int | None = None
    generation_horizon_count: int | None = None
    generation_lead_value: int | None = None
    generation_lead_unit: str = MaintenanceGenerationLeadUnit.DAYS.value
    sensor_id: str | None = None
    sensor_threshold: str | None = None
    sensor_direction: str | None = None
    sensor_reset_rule: str = ""
    requires_shutdown: bool = False
    approval_required: bool = False
    auto_generate_work_order: bool = False
    is_active: bool = True
    notes: str = ""


@dataclass(frozen=True)
class MaintenancePreventivePlanUpdateCommand:
    plan_id: str
    site_id: str | None = None
    plan_code: str | None = None
    name: str | None = None
    asset_id: str | None = None
    component_id: str | None = None
    system_id: str | None = None
    description: str | None = None
    status: str | None = None
    plan_type: str | None = None
    priority: str | None = None
    trigger_mode: str | None = None
    schedule_policy: str | None = None
    calendar_frequency_unit: str | None = None
    calendar_frequency_value: int | None = None
    generation_horizon_count: int | None = None
    generation_lead_value: int | None = None
    generation_lead_unit: str | None = None
    sensor_id: str | None = None
    sensor_threshold: str | None = None
    sensor_direction: str | None = None
    sensor_reset_rule: str | None = None
    requires_shutdown: bool | None = None
    approval_required: bool | None = None
    auto_generate_work_order: bool | None = None
    is_active: bool | None = None
    notes: str | None = None
    expected_version: int | None = None


@dataclass(frozen=True)
class MaintenancePreventivePlanTaskCreateCommand:
    plan_id: str
    task_template_id: str
    trigger_scope: str = MaintenancePlanTaskTriggerScope.INHERIT_PLAN.value
    trigger_mode_override: str | None = None
    calendar_frequency_unit_override: str | None = None
    calendar_frequency_value_override: int | None = None
    sensor_id_override: str | None = None
    sensor_threshold_override: str | None = None
    sensor_direction_override: str | None = None
    sequence_no: int | None = None
    is_mandatory: bool = True
    default_assigned_team_id: str | None = None
    estimated_minutes_override: int | None = None
    notes: str = ""


@dataclass(frozen=True)
class MaintenancePreventivePlanTaskUpdateCommand:
    plan_task_id: str
    task_template_id: str | None = None
    trigger_scope: str | None = None
    trigger_mode_override: str | None = None
    calendar_frequency_unit_override: str | None = None
    calendar_frequency_value_override: int | None = None
    sensor_id_override: str | None = None
    sensor_threshold_override: str | None = None
    sensor_direction_override: str | None = None
    sequence_no: int | None = None
    is_mandatory: bool | None = None
    default_assigned_team_id: str | None = None
    estimated_minutes_override: int | None = None
    notes: str | None = None
    expected_version: int | None = None


__all__ = [
    "MaintenancePreventiveChoiceDescriptor",
    "MaintenancePreventiveForecastRowDescriptor",
    "MaintenancePreventiveGenerationResultDescriptor",
    "MaintenancePreventivePlanCreateCommand",
    "MaintenancePreventivePlanDesktopDto",
    "MaintenancePreventivePlanTaskCreateCommand",
    "MaintenancePreventivePlanTaskDesktopDto",
    "MaintenancePreventivePlanTaskUpdateCommand",
    "MaintenancePreventivePlanUpdateCommand",
    "MaintenancePreventiveQueueRowDescriptor",
    "MaintenanceTaskStepTemplateCreateCommand",
    "MaintenanceTaskStepTemplateDesktopDto",
    "MaintenanceTaskStepTemplateUpdateCommand",
    "MaintenanceTaskTemplateCreateCommand",
    "MaintenanceTaskTemplateDesktopDto",
    "MaintenanceTaskTemplateUpdateCommand",
]
