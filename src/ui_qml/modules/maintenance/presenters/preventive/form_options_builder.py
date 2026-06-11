from __future__ import annotations

from .options import hint_level_options, option


def build_plan_form_options(desktop_api) -> dict[str, object]:
    return {
        "siteOptions": [
            option(opt.value, opt.label)
            for opt in desktop_api.list_sites(active_only=None)
        ],
        "assetOptions": [
            option(opt.value, opt.label)
            for opt in desktop_api.list_asset_options(active_only=None)
        ],
        "componentOptions": [
            option(opt.value, opt.label)
            for opt in desktop_api.list_component_options(active_only=None)
        ],
        "systemOptions": [
            option(opt.value, opt.label)
            for opt in desktop_api.list_system_options(active_only=None)
        ],
        "sensorOptions": [
            option(opt.value, opt.label)
            for opt in desktop_api.list_sensor_options(active_only=None)
        ],
        "statusOptions": [
            option(opt.value, opt.label)
            for opt in desktop_api.list_plan_statuses()
        ],
        "planTypeOptions": [
            option(opt.value, opt.label)
            for opt in desktop_api.list_plan_types()
        ],
        "priorityOptions": [
            option(opt.value, opt.label)
            for opt in desktop_api.list_priorities()
        ],
        "triggerModeOptions": [
            option(opt.value, opt.label)
            for opt in desktop_api.list_trigger_modes()
        ],
        "schedulePolicyOptions": [
            option(opt.value, opt.label)
            for opt in desktop_api.list_schedule_policies()
        ],
        "calendarFrequencyUnitOptions": [
            option(opt.value, opt.label)
            for opt in desktop_api.list_calendar_frequency_units()
        ],
        "generationLeadUnitOptions": [
            option(opt.value, opt.label)
            for opt in desktop_api.list_generation_lead_units()
        ],
        "sensorDirectionOptions": [
            option(opt.value, opt.label)
            for opt in desktop_api.list_sensor_directions()
        ],
    }


def build_plan_task_form_options(desktop_api) -> dict[str, object]:
    return {
        "taskTemplateOptions": [
            option(row.id, f"{row.task_template_code} - {row.name}")
            for row in desktop_api.list_task_templates(active_only=None)
        ],
        "triggerScopeOptions": [
            option(opt.value, opt.label)
            for opt in desktop_api.list_plan_task_trigger_scopes()
        ],
        "triggerModeOptions": [
            option(opt.value, opt.label)
            for opt in desktop_api.list_trigger_modes()
        ],
        "calendarFrequencyUnitOptions": [
            option(opt.value, opt.label)
            for opt in desktop_api.list_calendar_frequency_units()
        ],
        "sensorOptions": [
            option(opt.value, opt.label)
            for opt in desktop_api.list_sensor_options(active_only=None)
        ],
        "sensorDirectionOptions": [
            option(opt.value, opt.label)
            for opt in desktop_api.list_sensor_directions()
        ],
    }


def build_template_form_options(
    task_template_type_options: list[dict[str, str]],
    desktop_api,
) -> dict[str, object]:
    return {
        "maintenanceTypeOptions": [
            opt
            for opt in task_template_type_options
            if opt["value"] != "all"
        ],
        "statusOptions": [
            option(opt.value, opt.label)
            for opt in desktop_api.list_task_template_statuses()
        ],
    }


def build_step_form_options() -> dict[str, object]:
    return {
        "hintLevelOptions": hint_level_options(),
    }
