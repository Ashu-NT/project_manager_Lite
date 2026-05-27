from __future__ import annotations

from typing import Any

from src.core.modules.maintenance.api.desktop import (
    MaintenancePreventiveDesktopApi,
    MaintenancePreventivePlanCreateCommand,
    MaintenancePreventivePlanTaskCreateCommand,
    MaintenancePreventivePlanTaskUpdateCommand,
    MaintenancePreventivePlanUpdateCommand,
    MaintenanceTaskStepTemplateCreateCommand,
    MaintenanceTaskStepTemplateUpdateCommand,
    MaintenanceTaskTemplateCreateCommand,
    MaintenanceTaskTemplateUpdateCommand,
    build_maintenance_preventive_desktop_api,
)
from src.ui_qml.modules.maintenance.view_models.preventive import (
    MaintenancePreventiveMetricViewModel,
    MaintenancePreventiveOverviewViewModel,
    MaintenancePreventiveWorkspaceViewModel,
)


def _option(value: str, label: str) -> dict[str, str]:
    return {"value": value, "label": label}


def _active_filter_options() -> list[dict[str, str]]:
    return [
        _option("all", "All records"),
        _option("active", "Active only"),
        _option("inactive", "Inactive only"),
    ]


def _hint_level_options() -> list[dict[str, str]]:
    return [
        _option("", "No hint level"),
        _option("LOW", "Low"),
        _option("MEDIUM", "Medium"),
        _option("HIGH", "High"),
        _option("CRITICAL", "Critical"),
    ]


class MaintenancePreventiveWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: MaintenancePreventiveDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_maintenance_preventive_desktop_api()

    def build_workspace_state(
        self,
        *,
        queue_site_filter: str = "all",
        queue_due_state_filter: str = "all",
        queue_search_text: str = "",
        selected_queue_plan_id: str | None = None,
        plan_site_filter: str = "all",
        plan_asset_filter: str = "all",
        plan_system_filter: str = "all",
        plan_active_filter: str = "all",
        plan_status_filter: str = "all",
        plan_type_filter: str = "all",
        plan_trigger_mode_filter: str = "all",
        plan_search_text: str = "",
        selected_plan_id: str | None = None,
        selected_plan_task_id: str | None = None,
        template_active_filter: str = "all",
        template_maintenance_type_filter: str = "all",
        template_status_filter: str = "all",
        template_search_text: str = "",
        selected_task_template_id: str | None = None,
        selected_task_step_id: str | None = None,
        generation_results: list[dict[str, object]] | None = None,
    ) -> MaintenancePreventiveWorkspaceViewModel:
        site_filter_options = [
            _option("all", "All sites"),
            *(
                _option(option.value, option.label)
                for option in self._desktop_api.list_sites(active_only=None)
            ),
        ]
        due_state_options = [
            _option("all", "All due states"),
            *(
                _option(option.value, option.label)
                for option in self._desktop_api.list_due_states()
            ),
        ]
        plan_status_options = [
            _option("all", "All statuses"),
            *(
                _option(option.value, option.label)
                for option in self._desktop_api.list_plan_statuses()
            ),
        ]
        plan_type_options = [
            _option("all", "All plan types"),
            *(
                _option(option.value, option.label)
                for option in self._desktop_api.list_plan_types()
            ),
        ]
        trigger_mode_options = [
            _option("all", "All trigger modes"),
            *(
                _option(option.value, option.label)
                for option in self._desktop_api.list_trigger_modes()
            ),
        ]
        task_template_status_options = [
            _option("all", "All template statuses"),
            *(
                _option(option.value, option.label)
                for option in self._desktop_api.list_task_template_statuses()
            ),
        ]
        task_template_type_options = self._build_task_template_type_options()
        active_filter_options = _active_filter_options()

        normalized_queue_site_filter = self._normalize_filter(
            queue_site_filter,
            site_filter_options,
        )
        normalized_queue_due_state_filter = self._normalize_filter(
            queue_due_state_filter,
            due_state_options,
        )
        normalized_plan_site_filter = self._normalize_filter(
            plan_site_filter,
            site_filter_options,
        )

        asset_filter_options = [
            _option("all", "All assets"),
            *(
                _option(option.value, option.label)
                for option in self._desktop_api.list_asset_options(
                    active_only=None,
                    site_id=None
                    if normalized_plan_site_filter == "all"
                    else normalized_plan_site_filter,
                )
            ),
        ]
        system_filter_options = [
            _option("all", "All systems"),
            *(
                _option(option.value, option.label)
                for option in self._desktop_api.list_system_options(
                    active_only=None,
                    site_id=None
                    if normalized_plan_site_filter == "all"
                    else normalized_plan_site_filter,
                )
            ),
        ]
        normalized_plan_asset_filter = self._normalize_filter(
            plan_asset_filter,
            asset_filter_options,
        )
        normalized_plan_system_filter = self._normalize_filter(
            plan_system_filter,
            system_filter_options,
        )
        normalized_plan_active_filter = self._normalize_filter(
            plan_active_filter,
            active_filter_options,
        )
        normalized_plan_status_filter = self._normalize_filter(
            plan_status_filter,
            plan_status_options,
        )
        normalized_plan_type_filter = self._normalize_filter(
            plan_type_filter,
            plan_type_options,
        )
        normalized_plan_trigger_mode_filter = self._normalize_filter(
            plan_trigger_mode_filter,
            trigger_mode_options,
        )
        normalized_template_active_filter = self._normalize_filter(
            template_active_filter,
            active_filter_options,
        )
        normalized_template_maintenance_type_filter = self._normalize_filter(
            template_maintenance_type_filter,
            task_template_type_options,
        )
        normalized_template_status_filter = self._normalize_filter(
            template_status_filter,
            task_template_status_options,
        )

        normalized_queue_search = (queue_search_text or "").strip()
        normalized_plan_search = (plan_search_text or "").strip()
        normalized_template_search = (template_search_text or "").strip()

        queue_rows_all = self._desktop_api.list_due_candidates(
            site_id=None
            if normalized_queue_site_filter == "all"
            else normalized_queue_site_filter,
        )
        filtered_queue_rows = tuple(
            row
            for row in queue_rows_all
            if (
                normalized_queue_due_state_filter == "all"
                or row.due_state == normalized_queue_due_state_filter
            )
            and self._matches_search(
                normalized_queue_search,
                row.plan_code,
                row.plan_label,
                row.anchor_label,
                row.plan_status,
                row.due_state,
                row.due_reason,
                row.trigger_label,
                row.generation_target_label,
            )
        )
        resolved_queue_plan_id = self._resolve_selected_id(
            selected_queue_plan_id,
            filtered_queue_rows,
            id_attr="plan_id",
        )
        selected_queue_plan = next(
            (row for row in filtered_queue_rows if row.plan_id == resolved_queue_plan_id),
            None,
        )
        selected_queue_plan_detail = (
            self._desktop_api.get_preventive_plan(resolved_queue_plan_id)
            if resolved_queue_plan_id
            else None
        )
        forecast_rows = (
            self._desktop_api.preview_plan_schedule(plan_id=resolved_queue_plan_id)
            if resolved_queue_plan_id
            else ()
        )

        plan_rows_all = self._desktop_api.list_preventive_plans(
            active_only=self._to_active_only(normalized_plan_active_filter),
            site_id=None if normalized_plan_site_filter == "all" else normalized_plan_site_filter,
            asset_id=None if normalized_plan_asset_filter == "all" else normalized_plan_asset_filter,
            system_id=None if normalized_plan_system_filter == "all" else normalized_plan_system_filter,
            status=None if normalized_plan_status_filter == "all" else normalized_plan_status_filter,
            plan_type=None if normalized_plan_type_filter == "all" else normalized_plan_type_filter,
            trigger_mode=None
            if normalized_plan_trigger_mode_filter == "all"
            else normalized_plan_trigger_mode_filter,
            search_text=normalized_plan_search,
        )
        resolved_plan_id = self._resolve_selected_id(selected_plan_id, plan_rows_all)
        selected_plan = next((row for row in plan_rows_all if row.id == resolved_plan_id), None)
        plan_task_rows = (
            self._desktop_api.list_plan_tasks(plan_id=resolved_plan_id)
            if resolved_plan_id
            else ()
        )
        resolved_plan_task_id = self._resolve_selected_id(
            selected_plan_task_id,
            plan_task_rows,
        )
        selected_plan_task = next(
            (row for row in plan_task_rows if row.id == resolved_plan_task_id),
            None,
        )

        template_rows_all = self._desktop_api.list_task_templates(
            active_only=self._to_active_only(normalized_template_active_filter),
            maintenance_type=None
            if normalized_template_maintenance_type_filter == "all"
            else normalized_template_maintenance_type_filter,
            template_status=None
            if normalized_template_status_filter == "all"
            else normalized_template_status_filter,
            search_text=normalized_template_search,
        )
        resolved_task_template_id = self._resolve_selected_id(
            selected_task_template_id,
            template_rows_all,
        )
        selected_task_template = next(
            (row for row in template_rows_all if row.id == resolved_task_template_id),
            None,
        )
        step_rows = (
            self._desktop_api.list_task_step_templates(
                task_template_id=resolved_task_template_id,
                active_only=None,
            )
            if resolved_task_template_id
            else ()
        )
        resolved_task_step_id = self._resolve_selected_id(
            selected_task_step_id,
            step_rows,
        )
        selected_task_step = next(
            (row for row in step_rows if row.id == resolved_task_step_id),
            None,
        )

        queue_items = [self._queue_record(row) for row in filtered_queue_rows]
        plan_items = [self._plan_record(row) for row in plan_rows_all]
        plan_task_items = [self._plan_task_record(row) for row in plan_task_rows]
        template_items = [self._task_template_record(row) for row in template_rows_all]
        step_items = [self._task_step_record(row) for row in step_rows]

        generation_result_rows = generation_results or []

        return MaintenancePreventiveWorkspaceViewModel(
            overview=self._build_overview(
                queue_rows=queue_rows_all,
                plan_rows=plan_rows_all,
                task_template_rows=template_rows_all,
            ),
            queue_state={
                "siteOptions": site_filter_options,
                "dueStateOptions": due_state_options,
                "selectedSiteFilter": normalized_queue_site_filter,
                "selectedDueStateFilter": normalized_queue_due_state_filter,
                "searchText": normalized_queue_search,
                "plans": {
                    "title": "Generation Queue",
                    "subtitle": "Due, due-soon, blocked, and inactive preventive plans ready for review and work generation.",
                    "emptyState": self._build_queue_empty_state(
                        queue_rows_all=queue_rows_all,
                        filtered_queue_rows=filtered_queue_rows,
                        queue_search_text=normalized_queue_search,
                        queue_site_filter=normalized_queue_site_filter,
                        queue_due_state_filter=normalized_queue_due_state_filter,
                    ),
                    "items": queue_items,
                },
                "selectedPlanId": resolved_queue_plan_id,
                "selectedPlan": self._plan_detail(
                    selected_queue_plan_detail,
                    empty_state="Select a preventive plan to preview upcoming due instances and work-generation readiness.",
                    queue_row=selected_queue_plan,
                ),
                "forecastRows": {
                    "title": "Forecast",
                    "subtitle": "Preview generation windows, planner state, and instance outcomes for the selected plan.",
                    "emptyState": "Select a preventive plan to preview the generated schedule horizon.",
                    "items": [
                        self._forecast_record(row)
                        for row in forecast_rows
                    ],
                },
                "generationResults": {
                    "title": "Latest generation results",
                    "subtitle": "Review work requests or work orders created by the most recent generation run.",
                    "emptyState": "Generate due work to review the created records here.",
                    "items": list(generation_result_rows),
                },
            },
            plan_library_state={
                "siteOptions": site_filter_options,
                "assetOptions": asset_filter_options,
                "systemOptions": system_filter_options,
                "activeOptions": active_filter_options,
                "statusOptions": plan_status_options,
                "planTypeOptions": plan_type_options,
                "triggerModeOptions": trigger_mode_options,
                "selectedSiteFilter": normalized_plan_site_filter,
                "selectedAssetFilter": normalized_plan_asset_filter,
                "selectedSystemFilter": normalized_plan_system_filter,
                "selectedActiveFilter": normalized_plan_active_filter,
                "selectedStatusFilter": normalized_plan_status_filter,
                "selectedPlanTypeFilter": normalized_plan_type_filter,
                "selectedTriggerModeFilter": normalized_plan_trigger_mode_filter,
                "searchText": normalized_plan_search,
                "plans": {
                    "title": "Plan Library",
                    "subtitle": "Maintain preventive plans, anchor context, trigger rules, and lifecycle status on the typed desktop API.",
                    "emptyState": self._build_plan_empty_state(
                        plan_rows_all=plan_rows_all,
                        plan_search_text=normalized_plan_search,
                        site_filter=normalized_plan_site_filter,
                        asset_filter=normalized_plan_asset_filter,
                        system_filter=normalized_plan_system_filter,
                        active_filter=normalized_plan_active_filter,
                        status_filter=normalized_plan_status_filter,
                        plan_type_filter=normalized_plan_type_filter,
                        trigger_mode_filter=normalized_plan_trigger_mode_filter,
                    ),
                    "items": plan_items,
                },
                "selectedPlanId": resolved_plan_id,
                "selectedPlan": self._plan_detail(
                    selected_plan,
                    empty_state="Select a preventive plan to inspect trigger settings, lead generation, and plan-task composition.",
                ),
                "planTasks": {
                    "title": "Plan Tasks",
                    "subtitle": "Plan-task overrides, sequence order, and trigger-scope adjustments for the selected plan.",
                    "emptyState": (
                        "Select a preventive plan to review its plan-task overrides."
                        if not resolved_plan_id
                        else "No plan tasks are configured for the selected preventive plan yet."
                    ),
                    "items": plan_task_items,
                },
                "selectedPlanTaskId": resolved_plan_task_id,
                "selectedPlanTask": self._plan_task_detail(selected_plan_task),
            },
            template_library_state={
                "activeOptions": active_filter_options,
                "maintenanceTypeOptions": task_template_type_options,
                "statusOptions": task_template_status_options,
                "selectedActiveFilter": normalized_template_active_filter,
                "selectedMaintenanceTypeFilter": normalized_template_maintenance_type_filter,
                "selectedStatusFilter": normalized_template_status_filter,
                "searchText": normalized_template_search,
                "templates": {
                    "title": "Task Templates",
                    "subtitle": "Reusable preventive task templates with versioned instructions, permit flags, and step libraries.",
                    "emptyState": self._build_template_empty_state(
                        template_rows_all=template_rows_all,
                        search_text=normalized_template_search,
                        active_filter=normalized_template_active_filter,
                        maintenance_type_filter=normalized_template_maintenance_type_filter,
                        status_filter=normalized_template_status_filter,
                    ),
                    "items": template_items,
                },
                "selectedTaskTemplateId": resolved_task_template_id,
                "selectedTaskTemplate": self._task_template_detail(selected_task_template),
                "steps": {
                    "title": "Task Steps",
                    "subtitle": "Step instructions, hint levels, confirmation flags, and measurement expectations for the selected template.",
                    "emptyState": (
                        "Select a task template to review its step library."
                        if not resolved_task_template_id
                        else "No step templates are configured for the selected task template yet."
                    ),
                    "items": step_items,
                },
                "selectedTaskStepId": resolved_task_step_id,
                "selectedTaskStep": self._task_step_detail(selected_task_step),
            },
            plan_form_options={
                "siteOptions": [
                    _option(option.value, option.label)
                    for option in self._desktop_api.list_sites(active_only=None)
                ],
                "assetOptions": [
                    _option(option.value, option.label)
                    for option in self._desktop_api.list_asset_options(active_only=None)
                ],
                "componentOptions": [
                    _option(option.value, option.label)
                    for option in self._desktop_api.list_component_options(active_only=None)
                ],
                "systemOptions": [
                    _option(option.value, option.label)
                    for option in self._desktop_api.list_system_options(active_only=None)
                ],
                "sensorOptions": [
                    _option(option.value, option.label)
                    for option in self._desktop_api.list_sensor_options(active_only=None)
                ],
                "statusOptions": [
                    _option(option.value, option.label)
                    for option in self._desktop_api.list_plan_statuses()
                ],
                "planTypeOptions": [
                    _option(option.value, option.label)
                    for option in self._desktop_api.list_plan_types()
                ],
                "priorityOptions": [
                    _option(option.value, option.label)
                    for option in self._desktop_api.list_priorities()
                ],
                "triggerModeOptions": [
                    _option(option.value, option.label)
                    for option in self._desktop_api.list_trigger_modes()
                ],
                "schedulePolicyOptions": [
                    _option(option.value, option.label)
                    for option in self._desktop_api.list_schedule_policies()
                ],
                "calendarFrequencyUnitOptions": [
                    _option(option.value, option.label)
                    for option in self._desktop_api.list_calendar_frequency_units()
                ],
                "generationLeadUnitOptions": [
                    _option(option.value, option.label)
                    for option in self._desktop_api.list_generation_lead_units()
                ],
                "sensorDirectionOptions": [
                    _option(option.value, option.label)
                    for option in self._desktop_api.list_sensor_directions()
                ],
            },
            plan_task_form_options={
                "taskTemplateOptions": [
                    _option(row.id, f"{row.task_template_code} - {row.name}")
                    for row in self._desktop_api.list_task_templates(active_only=None)
                ],
                "triggerScopeOptions": [
                    _option(option.value, option.label)
                    for option in self._desktop_api.list_plan_task_trigger_scopes()
                ],
                "triggerModeOptions": [
                    _option(option.value, option.label)
                    for option in self._desktop_api.list_trigger_modes()
                ],
                "calendarFrequencyUnitOptions": [
                    _option(option.value, option.label)
                    for option in self._desktop_api.list_calendar_frequency_units()
                ],
                "sensorOptions": [
                    _option(option.value, option.label)
                    for option in self._desktop_api.list_sensor_options(active_only=None)
                ],
                "sensorDirectionOptions": [
                    _option(option.value, option.label)
                    for option in self._desktop_api.list_sensor_directions()
                ],
            },
            template_form_options={
                "maintenanceTypeOptions": [
                    option
                    for option in task_template_type_options
                    if option["value"] != "all"
                ],
                "statusOptions": [
                    _option(option.value, option.label)
                    for option in self._desktop_api.list_task_template_statuses()
                ],
            },
            step_form_options={
                "hintLevelOptions": _hint_level_options(),
            },
        )

    def create_plan(self, payload: dict[str, Any]) -> None:
        self._desktop_api.create_preventive_plan(
            MaintenancePreventivePlanCreateCommand(
                site_id=self._require_text(payload, "siteId", "Choose a site before saving."),
                plan_code=self._require_text(payload, "planCode", "Plan code is required."),
                name=self._require_text(payload, "name", "Plan name is required."),
                asset_id=self._optional_text(payload, "assetId"),
                component_id=self._optional_text(payload, "componentId"),
                system_id=self._optional_text(payload, "systemId"),
                description=self._optional_text(payload, "description") or "",
                status=self._optional_text(payload, "status") or "ACTIVE",
                plan_type=self._optional_text(payload, "planType") or "PREVENTIVE",
                priority=self._optional_text(payload, "priority") or "MEDIUM",
                trigger_mode=self._optional_text(payload, "triggerMode") or "CALENDAR",
                schedule_policy=self._optional_text(payload, "schedulePolicy") or "FIXED",
                calendar_frequency_unit=self._optional_text(payload, "calendarFrequencyUnit"),
                calendar_frequency_value=self._optional_int(payload, "calendarFrequencyValue"),
                generation_horizon_count=self._optional_int(payload, "generationHorizonCount"),
                generation_lead_value=self._optional_int(payload, "generationLeadValue"),
                generation_lead_unit=self._optional_text(payload, "generationLeadUnit") or "DAYS",
                sensor_id=self._optional_text(payload, "sensorId"),
                sensor_threshold=self._optional_text(payload, "sensorThreshold"),
                sensor_direction=self._optional_text(payload, "sensorDirection"),
                sensor_reset_rule=self._optional_text(payload, "sensorResetRule") or "",
                requires_shutdown=self._optional_bool(payload, "requiresShutdown", False),
                approval_required=self._optional_bool(payload, "approvalRequired", False),
                auto_generate_work_order=self._optional_bool(payload, "autoGenerateWorkOrder", False),
                is_active=self._optional_bool(payload, "isActive", True),
                notes=self._optional_text(payload, "notes") or "",
            )
        )

    def update_plan(self, payload: dict[str, Any]) -> None:
        self._desktop_api.update_preventive_plan(
            MaintenancePreventivePlanUpdateCommand(
                plan_id=self._require_text(payload, "planId", "Plan ID is required."),
                site_id=self._optional_text(payload, "siteId"),
                plan_code=self._optional_text(payload, "planCode"),
                name=self._optional_text(payload, "name"),
                asset_id=self._optional_text(payload, "assetId"),
                component_id=self._optional_text(payload, "componentId"),
                system_id=self._optional_text(payload, "systemId"),
                description=self._optional_text(payload, "description"),
                status=self._optional_text(payload, "status"),
                plan_type=self._optional_text(payload, "planType"),
                priority=self._optional_text(payload, "priority"),
                trigger_mode=self._optional_text(payload, "triggerMode"),
                schedule_policy=self._optional_text(payload, "schedulePolicy"),
                calendar_frequency_unit=self._optional_text(payload, "calendarFrequencyUnit"),
                calendar_frequency_value=self._optional_int(payload, "calendarFrequencyValue"),
                generation_horizon_count=self._optional_int(payload, "generationHorizonCount"),
                generation_lead_value=self._optional_int(payload, "generationLeadValue"),
                generation_lead_unit=self._optional_text(payload, "generationLeadUnit"),
                sensor_id=self._optional_text(payload, "sensorId"),
                sensor_threshold=self._optional_text(payload, "sensorThreshold"),
                sensor_direction=self._optional_text(payload, "sensorDirection"),
                sensor_reset_rule=self._optional_text(payload, "sensorResetRule"),
                requires_shutdown=self._optional_optional_bool(payload, "requiresShutdown"),
                approval_required=self._optional_optional_bool(payload, "approvalRequired"),
                auto_generate_work_order=self._optional_optional_bool(payload, "autoGenerateWorkOrder"),
                is_active=self._optional_optional_bool(payload, "isActive"),
                notes=self._optional_text(payload, "notes"),
                expected_version=self._require_int(
                    payload,
                    "expectedVersion",
                    "Expected version is required before saving.",
                ),
            )
        )

    def toggle_plan_active(
        self,
        *,
        plan_id: str,
        is_active: bool,
        expected_version: int,
    ) -> None:
        self._desktop_api.update_preventive_plan(
            MaintenancePreventivePlanUpdateCommand(
                plan_id=plan_id,
                is_active=is_active,
                expected_version=expected_version,
            )
        )

    def create_plan_task(self, payload: dict[str, Any]) -> None:
        self._desktop_api.create_plan_task(
            MaintenancePreventivePlanTaskCreateCommand(
                plan_id=self._require_text(payload, "planId", "Choose a preventive plan first."),
                task_template_id=self._require_text(
                    payload,
                    "taskTemplateId",
                    "Choose a task template before saving.",
                ),
                trigger_scope=self._optional_text(payload, "triggerScope") or "INHERIT_PLAN",
                trigger_mode_override=self._optional_text(payload, "triggerModeOverride"),
                calendar_frequency_unit_override=self._optional_text(
                    payload,
                    "calendarFrequencyUnitOverride",
                ),
                calendar_frequency_value_override=self._optional_int(
                    payload,
                    "calendarFrequencyValueOverride",
                ),
                sensor_id_override=self._optional_text(payload, "sensorIdOverride"),
                sensor_threshold_override=self._optional_text(payload, "sensorThresholdOverride"),
                sensor_direction_override=self._optional_text(payload, "sensorDirectionOverride"),
                sequence_no=self._optional_int(payload, "sequenceNo"),
                is_mandatory=self._optional_bool(payload, "isMandatory", True),
                default_assigned_team_id=self._optional_text(payload, "defaultAssignedTeamId"),
                estimated_minutes_override=self._optional_int(payload, "estimatedMinutesOverride"),
                notes=self._optional_text(payload, "notes") or "",
            )
        )

    def update_plan_task(self, payload: dict[str, Any]) -> None:
        self._desktop_api.update_plan_task(
            MaintenancePreventivePlanTaskUpdateCommand(
                plan_task_id=self._require_text(
                    payload,
                    "planTaskId",
                    "Plan task ID is required.",
                ),
                task_template_id=self._optional_text(payload, "taskTemplateId"),
                trigger_scope=self._optional_text(payload, "triggerScope"),
                trigger_mode_override=self._optional_text(payload, "triggerModeOverride"),
                calendar_frequency_unit_override=self._optional_text(
                    payload,
                    "calendarFrequencyUnitOverride",
                ),
                calendar_frequency_value_override=self._optional_int(
                    payload,
                    "calendarFrequencyValueOverride",
                ),
                sensor_id_override=self._optional_text(payload, "sensorIdOverride"),
                sensor_threshold_override=self._optional_text(payload, "sensorThresholdOverride"),
                sensor_direction_override=self._optional_text(payload, "sensorDirectionOverride"),
                sequence_no=self._optional_int(payload, "sequenceNo"),
                is_mandatory=self._optional_optional_bool(payload, "isMandatory"),
                default_assigned_team_id=self._optional_text(payload, "defaultAssignedTeamId"),
                estimated_minutes_override=self._optional_int(payload, "estimatedMinutesOverride"),
                notes=self._optional_text(payload, "notes"),
                expected_version=self._require_int(
                    payload,
                    "expectedVersion",
                    "Expected version is required before saving.",
                ),
            )
        )

    def create_task_template(self, payload: dict[str, Any]) -> None:
        self._desktop_api.create_task_template(
            MaintenanceTaskTemplateCreateCommand(
                task_template_code=self._require_text(
                    payload,
                    "taskTemplateCode",
                    "Task template code is required.",
                ),
                name=self._require_text(payload, "name", "Task template name is required."),
                description=self._optional_text(payload, "description") or "",
                maintenance_type=self._optional_text(payload, "maintenanceType") or "PREVENTIVE",
                revision_no=self._require_int(
                    payload,
                    "revisionNo",
                    "Revision number is required.",
                ),
                template_status=self._optional_text(payload, "templateStatus") or "DRAFT",
                estimated_minutes=self._optional_int(payload, "estimatedMinutes"),
                required_skill=self._optional_text(payload, "requiredSkill") or "",
                requires_shutdown=self._optional_bool(payload, "requiresShutdown", False),
                requires_permit=self._optional_bool(payload, "requiresPermit", False),
                is_active=self._optional_bool(payload, "isActive", True),
                notes=self._optional_text(payload, "notes") or "",
            )
        )

    def update_task_template(self, payload: dict[str, Any]) -> None:
        self._desktop_api.update_task_template(
            MaintenanceTaskTemplateUpdateCommand(
                task_template_id=self._require_text(
                    payload,
                    "taskTemplateId",
                    "Task template ID is required.",
                ),
                task_template_code=self._optional_text(payload, "taskTemplateCode"),
                name=self._optional_text(payload, "name"),
                description=self._optional_text(payload, "description"),
                maintenance_type=self._optional_text(payload, "maintenanceType"),
                revision_no=self._optional_int(payload, "revisionNo"),
                template_status=self._optional_text(payload, "templateStatus"),
                estimated_minutes=self._optional_int(payload, "estimatedMinutes"),
                required_skill=self._optional_text(payload, "requiredSkill"),
                requires_shutdown=self._optional_optional_bool(payload, "requiresShutdown"),
                requires_permit=self._optional_optional_bool(payload, "requiresPermit"),
                is_active=self._optional_optional_bool(payload, "isActive"),
                notes=self._optional_text(payload, "notes"),
                expected_version=self._require_int(
                    payload,
                    "expectedVersion",
                    "Expected version is required before saving.",
                ),
            )
        )

    def toggle_task_template_active(
        self,
        *,
        task_template_id: str,
        is_active: bool,
        expected_version: int,
    ) -> None:
        self._desktop_api.update_task_template(
            MaintenanceTaskTemplateUpdateCommand(
                task_template_id=task_template_id,
                is_active=is_active,
                expected_version=expected_version,
            )
        )

    def create_task_step(self, payload: dict[str, Any]) -> None:
        self._desktop_api.create_task_step_template(
            MaintenanceTaskStepTemplateCreateCommand(
                task_template_id=self._require_text(
                    payload,
                    "taskTemplateId",
                    "Choose a task template before saving a step.",
                ),
                step_number=self._require_int(
                    payload,
                    "stepNumber",
                    "Step number is required.",
                ),
                sort_order=self._optional_int(payload, "sortOrder"),
                instruction=self._require_text(
                    payload,
                    "instruction",
                    "Instruction is required.",
                ),
                expected_result=self._optional_text(payload, "expectedResult") or "",
                hint_level=self._optional_text(payload, "hintLevel") or "",
                hint_text=self._optional_text(payload, "hintText") or "",
                requires_confirmation=self._optional_bool(payload, "requiresConfirmation", False),
                requires_measurement=self._optional_bool(payload, "requiresMeasurement", False),
                requires_photo=self._optional_bool(payload, "requiresPhoto", False),
                measurement_unit=self._optional_text(payload, "measurementUnit") or "",
                is_active=self._optional_bool(payload, "isActive", True),
                notes=self._optional_text(payload, "notes") or "",
            )
        )

    def update_task_step(self, payload: dict[str, Any]) -> None:
        self._desktop_api.update_task_step_template(
            MaintenanceTaskStepTemplateUpdateCommand(
                task_step_template_id=self._require_text(
                    payload,
                    "taskStepTemplateId",
                    "Task step template ID is required.",
                ),
                step_number=self._optional_int(payload, "stepNumber"),
                sort_order=self._optional_int(payload, "sortOrder"),
                instruction=self._optional_text(payload, "instruction"),
                expected_result=self._optional_text(payload, "expectedResult"),
                hint_level=self._optional_text(payload, "hintLevel"),
                hint_text=self._optional_text(payload, "hintText"),
                requires_confirmation=self._optional_optional_bool(payload, "requiresConfirmation"),
                requires_measurement=self._optional_optional_bool(payload, "requiresMeasurement"),
                requires_photo=self._optional_optional_bool(payload, "requiresPhoto"),
                measurement_unit=self._optional_text(payload, "measurementUnit"),
                is_active=self._optional_optional_bool(payload, "isActive"),
                notes=self._optional_text(payload, "notes"),
                expected_version=self._require_int(
                    payload,
                    "expectedVersion",
                    "Expected version is required before saving.",
                ),
            )
        )

    def toggle_task_step_active(
        self,
        *,
        task_step_template_id: str,
        is_active: bool,
        expected_version: int,
    ) -> None:
        self._desktop_api.update_task_step_template(
            MaintenanceTaskStepTemplateUpdateCommand(
                task_step_template_id=task_step_template_id,
                is_active=is_active,
                expected_version=expected_version,
            )
        )

    def generate_due_work(self, *, plan_id: str) -> list[dict[str, object]]:
        rows = self._desktop_api.generate_due_work(plan_id=plan_id)
        return [self._generation_result_record(row) for row in rows]

    def regenerate_plan_schedule(self, *, plan_id: str) -> None:
        self._desktop_api.regenerate_plan_schedule(plan_id=plan_id)

    @staticmethod
    def _build_overview(
        *,
        queue_rows,
        plan_rows,
        task_template_rows,
    ) -> MaintenancePreventiveOverviewViewModel:
        due_count = sum(1 for row in queue_rows if row.due_state == "DUE")
        due_soon_count = sum(1 for row in queue_rows if row.is_due_soon)
        blocked_count = sum(1 for row in queue_rows if row.due_state == "BLOCKED")
        return MaintenancePreventiveOverviewViewModel(
            title="Preventive",
            subtitle=(
                "Preventive queue, plan-library governance, and task-template "
                "migration now run through the maintenance preventive desktop API."
            ),
            metrics=(
                MaintenancePreventiveMetricViewModel(
                    label="Queue",
                    value=str(len(queue_rows)),
                    supporting_text=(
                        f"{due_count} due, {due_soon_count} due soon, "
                        f"{blocked_count} blocked."
                    ),
                ),
                MaintenancePreventiveMetricViewModel(
                    label="Plans",
                    value=str(len(plan_rows)),
                    supporting_text=(
                        "Preventive plans currently available in the typed library."
                    ),
                ),
                MaintenancePreventiveMetricViewModel(
                    label="Templates",
                    value=str(len(task_template_rows)),
                    supporting_text=(
                        "Reusable task templates and step libraries available for "
                        "plan tasks."
                    ),
                ),
            ),
        )

    @staticmethod
    def _queue_record(row) -> dict[str, object]:
        return {
            "id": row.plan_id,
            "title": row.plan_label,
            "subtitle": row.anchor_label,
            "statusLabel": row.due_state_label,
            "supportingText": f"{row.plan_status_label} | {row.trigger_label}",
            "metaText": f"Next due: {row.next_due_label} | {row.due_reason}",
            "canPrimaryAction": True,
            "canSecondaryAction": True,
            "canTertiaryAction": False,
            "state": {
                "planId": row.plan_id,
                "expectedVersion": row.version,
                "isDueSoon": row.is_due_soon,
                "canPrimaryAction": True,
                "canSecondaryAction": True,
            },
        }

    @staticmethod
    def _plan_record(row) -> dict[str, object]:
        plan_label = f"{row.plan_code} - {row.name}"
        return {
            "id": row.id,
            "title": plan_label,
            "subtitle": row.anchor_label,
            "statusLabel": row.status_label,
            "supportingText": f"{row.plan_type_label} | {row.trigger_summary}",
            "metaText": f"Tasks: {row.plan_task_count} | Next due: {row.next_due_label}",
            "canPrimaryAction": True,
            "canSecondaryAction": True,
            "canTertiaryAction": False,
            "state": {
                "planId": row.id,
                "isActive": row.is_active,
                "expectedVersion": row.version,
                "canPrimaryAction": True,
                "canSecondaryAction": True,
            },
        }

    @staticmethod
    def _plan_task_record(row) -> dict[str, object]:
        return {
            "id": row.id,
            "title": f"Step {row.sequence_no} - {row.task_template_label}",
            "subtitle": row.trigger_scope_label,
            "statusLabel": "Mandatory" if row.is_mandatory else "Optional",
            "supportingText": row.trigger_rule_summary or "Uses inherited trigger rules.",
            "metaText": f"Next due: {row.next_due_label} | Estimate: {row.estimated_minutes_override or '-'} min",
            "canPrimaryAction": True,
            "canSecondaryAction": False,
            "canTertiaryAction": False,
            "state": {
                "planTaskId": row.id,
                "expectedVersion": row.version,
                "canPrimaryAction": True,
                "canSecondaryAction": False,
            },
        }

    @staticmethod
    def _task_template_record(row) -> dict[str, object]:
        return {
            "id": row.id,
            "title": f"{row.task_template_code} - {row.name}",
            "subtitle": row.maintenance_type_label,
            "statusLabel": row.template_status_label,
            "supportingText": f"Revision {row.revision_no} | {row.step_count} steps | {row.active_label}",
            "metaText": f"Estimated minutes: {row.estimated_minutes or '-'} | Skill: {row.required_skill or '-'}",
            "canPrimaryAction": True,
            "canSecondaryAction": True,
            "canTertiaryAction": False,
            "state": {
                "taskTemplateId": row.id,
                "isActive": row.is_active,
                "expectedVersion": row.version,
                "canPrimaryAction": True,
                "canSecondaryAction": True,
            },
        }

    @staticmethod
    def _task_step_record(row) -> dict[str, object]:
        return {
            "id": row.id,
            "title": f"Step {row.step_number}",
            "subtitle": row.instruction,
            "statusLabel": row.active_label,
            "supportingText": row.expected_result or "No expected result provided.",
            "metaText": f"Hint: {row.hint_level_label or '-'} | Sort: {row.sort_order}",
            "canPrimaryAction": True,
            "canSecondaryAction": True,
            "canTertiaryAction": False,
            "state": {
                "taskStepTemplateId": row.id,
                "isActive": row.is_active,
                "expectedVersion": row.version,
                "canPrimaryAction": True,
                "canSecondaryAction": True,
            },
        }

    @staticmethod
    def _forecast_record(row) -> dict[str, object]:
        return {
            "id": row.instance_id,
            "title": row.due_at_label,
            "subtitle": row.instance_status_label,
            "statusLabel": row.planner_state_label,
            "supportingText": f"Window opens: {row.generation_window_opens_at_label}",
            "metaText": (
                f"WR: {row.generated_work_request_id or '-'} | "
                f"WO: {row.generated_work_order_id or '-'} | "
                f"Completed: {row.completed_at_label or '-'}"
            ),
            "canPrimaryAction": False,
            "canSecondaryAction": False,
            "canTertiaryAction": False,
            "state": {},
        }

    @staticmethod
    def _generation_result_record(row) -> dict[str, object]:
        target_id = row.generated_work_order_id or row.generated_work_request_id or row.plan_id
        return {
            "id": target_id,
            "title": row.plan_code,
            "subtitle": row.generation_target_label,
            "statusLabel": str(row.generated_task_count),
            "supportingText": (
                f"Work request: {row.generated_work_request_id or '-'} | "
                f"Work order: {row.generated_work_order_id or '-'}"
            ),
            "metaText": (
                f"Steps: {row.generated_step_count} | "
                f"{row.skipped_reason or 'Generation completed successfully.'}"
            ),
            "canPrimaryAction": False,
            "canSecondaryAction": False,
            "canTertiaryAction": False,
            "state": {},
        }

    @staticmethod
    def _plan_detail(row, *, empty_state: str, queue_row=None) -> dict[str, object]:
        if row is None:
            return {
                "id": "",
                "title": "No preventive plan selected",
                "statusLabel": "",
                "subtitle": "",
                "description": "",
                "emptyState": empty_state,
                "fields": [],
                "state": {},
            }
        due_state_label = getattr(queue_row, "due_state_label", "")
        due_reason = getattr(queue_row, "due_reason", "")
        plan_label = f"{row.plan_code} - {row.name}"
        return {
            "id": row.id,
            "title": plan_label,
            "statusLabel": row.status_label,
            "subtitle": f"{row.site_label} | {row.plan_type_label}",
            "description": row.description or "No preventive plan description provided.",
            "emptyState": "",
            "fields": [
                {"label": "Anchor", "value": row.anchor_label, "supportingText": row.component_label or row.system_label},
                {"label": "Trigger", "value": row.trigger_summary, "supportingText": row.trigger_mode_label},
                {"label": "Priority / Policy", "value": row.priority_label, "supportingText": row.schedule_policy_label},
                {
                    "label": "Generation lead",
                    "value": f"{row.generation_lead_value} {row.generation_lead_unit_label.lower()}",
                    "supportingText": f"Horizon: {row.generation_horizon_count}",
                },
                {
                    "label": "Next due",
                    "value": row.next_due_label or "-",
                    "supportingText": due_reason or due_state_label or row.next_due_counter or "",
                },
                {
                    "label": "Sensor",
                    "value": row.sensor_label or "-",
                    "supportingText": (
                        f"{row.sensor_direction_label} {row.sensor_threshold}".strip()
                        if row.sensor_label
                        else ""
                    ),
                },
                {"label": "Notes", "value": row.notes or "-", "supportingText": ""},
                {"label": "Version", "value": str(row.version), "supportingText": row.active_label},
            ],
            "state": {
                "planId": row.id,
                "siteId": row.site_id,
                "planCode": row.plan_code,
                "name": row.name,
                "assetId": row.asset_id or "",
                "componentId": row.component_id or "",
                "systemId": row.system_id or "",
                "description": row.description,
                "status": row.status,
                "planType": row.plan_type,
                "priority": row.priority,
                "triggerMode": row.trigger_mode,
                "schedulePolicy": row.schedule_policy,
                "calendarFrequencyUnit": row.calendar_frequency_unit,
                "calendarFrequencyValue": row.calendar_frequency_value,
                "generationHorizonCount": row.generation_horizon_count,
                "generationLeadValue": row.generation_lead_value,
                "generationLeadUnit": row.generation_lead_unit,
                "sensorId": row.sensor_id or "",
                "sensorThreshold": row.sensor_threshold,
                "sensorDirection": row.sensor_direction,
                "sensorResetRule": row.sensor_reset_rule,
                "requiresShutdown": row.requires_shutdown,
                "approvalRequired": row.approval_required,
                "autoGenerateWorkOrder": row.auto_generate_work_order,
                "isActive": row.is_active,
                "notes": row.notes,
                "expectedVersion": row.version,
                "canPrimaryAction": True,
                "canSecondaryAction": True,
            },
        }

    @staticmethod
    def _plan_task_detail(row) -> dict[str, object]:
        if row is None:
            return {
                "id": "",
                "title": "No plan task selected",
                "statusLabel": "",
                "subtitle": "",
                "description": "",
                "emptyState": "Select a plan task to review its sequence, trigger overrides, and estimate defaults.",
                "fields": [],
                "state": {},
            }
        return {
            "id": row.id,
            "title": row.task_template_label,
            "statusLabel": "Mandatory" if row.is_mandatory else "Optional",
            "subtitle": row.trigger_scope_label,
            "description": row.notes or "No plan-task notes provided.",
            "emptyState": "",
            "fields": [
                {"label": "Trigger", "value": row.trigger_rule_summary or row.trigger_scope_label, "supportingText": row.trigger_mode_override_label},
                {"label": "Sequence", "value": str(row.sequence_no), "supportingText": f"Estimate: {row.estimated_minutes_override or '-'} min"},
                {"label": "Sensor override", "value": row.sensor_label_override or "-", "supportingText": row.next_due_counter or ""},
                {"label": "Next due", "value": row.next_due_label or "-", "supportingText": row.next_due_counter or ""},
                {"label": "Assigned team", "value": row.default_assigned_team_id or "-", "supportingText": ""},
                {"label": "Version", "value": str(row.version), "supportingText": ""},
            ],
            "state": {
                "planTaskId": row.id,
                "planId": row.plan_id,
                "taskTemplateId": row.task_template_id,
                "triggerScope": row.trigger_scope,
                "triggerModeOverride": row.trigger_mode_override,
                "calendarFrequencyUnitOverride": "",
                "calendarFrequencyValueOverride": "",
                "sensorIdOverride": row.sensor_id_override or "",
                "sensorThresholdOverride": "",
                "sensorDirectionOverride": "",
                "sequenceNo": row.sequence_no,
                "isMandatory": row.is_mandatory,
                "defaultAssignedTeamId": row.default_assigned_team_id or "",
                "estimatedMinutesOverride": row.estimated_minutes_override,
                "notes": row.notes,
                "expectedVersion": row.version,
                "canPrimaryAction": True,
                "canSecondaryAction": False,
            },
        }

    @staticmethod
    def _task_template_detail(row) -> dict[str, object]:
        if row is None:
            return {
                "id": "",
                "title": "No task template selected",
                "statusLabel": "",
                "subtitle": "",
                "description": "",
                "emptyState": "Select a task template to inspect revision status, required skills, and its step library.",
                "fields": [],
                "state": {},
            }
        return {
            "id": row.id,
            "title": f"{row.task_template_code} - {row.name}",
            "statusLabel": row.template_status_label,
            "subtitle": row.maintenance_type_label,
            "description": row.description or "No task template description provided.",
            "emptyState": "",
            "fields": [
                {"label": "Revision", "value": str(row.revision_no), "supportingText": row.active_label},
                {"label": "Estimate", "value": str(row.estimated_minutes or "-"), "supportingText": "Minutes"},
                {"label": "Required skill", "value": row.required_skill or "-", "supportingText": ""},
                {
                    "label": "Permits / Shutdown",
                    "value": "Permit required" if row.requires_permit else "Permit not required",
                    "supportingText": "Shutdown required" if row.requires_shutdown else "No shutdown required",
                },
                {"label": "Notes", "value": row.notes or "-", "supportingText": ""},
                {"label": "Version", "value": str(row.version), "supportingText": f"{row.step_count} steps"},
            ],
            "state": {
                "taskTemplateId": row.id,
                "taskTemplateCode": row.task_template_code,
                "name": row.name,
                "description": row.description,
                "maintenanceType": row.maintenance_type,
                "revisionNo": row.revision_no,
                "templateStatus": row.template_status,
                "estimatedMinutes": row.estimated_minutes,
                "requiredSkill": row.required_skill,
                "requiresShutdown": row.requires_shutdown,
                "requiresPermit": row.requires_permit,
                "isActive": row.is_active,
                "notes": row.notes,
                "expectedVersion": row.version,
                "canPrimaryAction": True,
                "canSecondaryAction": True,
            },
        }

    @staticmethod
    def _task_step_detail(row) -> dict[str, object]:
        if row is None:
            return {
                "id": "",
                "title": "No task step selected",
                "statusLabel": "",
                "subtitle": "",
                "description": "",
                "emptyState": "Select a task step to review instructions, hinting, and confirmation requirements.",
                "fields": [],
                "state": {},
            }
        return {
            "id": row.id,
            "title": f"Step {row.step_number}",
            "statusLabel": row.active_label,
            "subtitle": row.instruction,
            "description": row.expected_result or "No expected result provided.",
            "emptyState": "",
            "fields": [
                {"label": "Sort order", "value": str(row.sort_order), "supportingText": row.hint_level_label or ""},
                {
                    "label": "Capture requirements",
                    "value": "Confirmation" if row.requires_confirmation else "No confirmation",
                    "supportingText": (
                        ("Measurement " if row.requires_measurement else "")
                        + ("Photo" if row.requires_photo else "")
                    ).strip() or "No extra capture requirements",
                },
                {"label": "Measurement unit", "value": row.measurement_unit or "-", "supportingText": ""},
                {"label": "Hint text", "value": row.hint_text or "-", "supportingText": ""},
                {"label": "Notes", "value": row.notes or "-", "supportingText": ""},
                {"label": "Version", "value": str(row.version), "supportingText": ""},
            ],
            "state": {
                "taskStepTemplateId": row.id,
                "taskTemplateId": row.task_template_id,
                "stepNumber": row.step_number,
                "sortOrder": row.sort_order,
                "instruction": row.instruction,
                "expectedResult": row.expected_result,
                "hintLevel": row.hint_level,
                "hintText": row.hint_text,
                "requiresConfirmation": row.requires_confirmation,
                "requiresMeasurement": row.requires_measurement,
                "requiresPhoto": row.requires_photo,
                "measurementUnit": row.measurement_unit,
                "isActive": row.is_active,
                "notes": row.notes,
                "expectedVersion": row.version,
                "canPrimaryAction": True,
                "canSecondaryAction": True,
            },
        }

    @staticmethod
    def _build_queue_empty_state(
        *,
        queue_rows_all,
        filtered_queue_rows,
        queue_search_text: str,
        queue_site_filter: str,
        queue_due_state_filter: str,
    ) -> str:
        if filtered_queue_rows:
            return ""
        if not queue_rows_all:
            return "No preventive plans are currently queued for review."
        if queue_search_text or queue_site_filter != "all" or queue_due_state_filter != "all":
            return "No queued preventive plans match the current filters."
        return "No preventive plans are currently queued for review."

    @staticmethod
    def _build_plan_empty_state(
        *,
        plan_rows_all,
        plan_search_text: str,
        site_filter: str,
        asset_filter: str,
        system_filter: str,
        active_filter: str,
        status_filter: str,
        plan_type_filter: str,
        trigger_mode_filter: str,
    ) -> str:
        if plan_rows_all:
            return ""
        if any(
            value != "all"
            for value in (
                site_filter,
                asset_filter,
                system_filter,
                active_filter,
                status_filter,
                plan_type_filter,
                trigger_mode_filter,
            )
        ) or plan_search_text:
            return "No preventive plans match the current filters."
        return "No preventive plans are available yet. Create a plan to start the library."

    @staticmethod
    def _build_template_empty_state(
        *,
        template_rows_all,
        search_text: str,
        active_filter: str,
        maintenance_type_filter: str,
        status_filter: str,
    ) -> str:
        if template_rows_all:
            return ""
        if (
            search_text
            or active_filter != "all"
            or maintenance_type_filter != "all"
            or status_filter != "all"
        ):
            return "No task templates match the current filters."
        return "No task templates are available yet. Create a template to seed the preventive library."

    @staticmethod
    def _matches_search(search_text: str, *values: str) -> bool:
        if not search_text:
            return True
        normalized = search_text.casefold()
        return any(normalized in str(value or "").casefold() for value in values)

    def _build_task_template_type_options(self) -> list[dict[str, str]]:
        seen: set[str] = set()
        options = [_option("all", "All maintenance types")]
        for option in self._desktop_api.list_task_template_maintenance_types(
            active_only=None
        ):
            key = str(option.value or "").strip().upper()
            if not key or key in seen:
                continue
            seen.add(key)
            options.append(_option(option.value, option.label))
        for fallback in (
            "PREVENTIVE",
            "INSPECTION",
            "LUBRICATION",
            "CALIBRATION",
            "CONDITION_BASED",
        ):
            if fallback in seen:
                continue
            seen.add(fallback)
            options.append(_option(fallback, fallback.replace("_", " ").title()))
        return options

    @staticmethod
    def _resolve_selected_id(selected_id: str | None, rows, *, id_attr: str = "id") -> str:
        normalized_id = (selected_id or "").strip()
        if normalized_id and any(getattr(row, id_attr) == normalized_id for row in rows):
            return normalized_id
        if rows:
            first_row = rows[0]
            return str(getattr(first_row, id_attr))
        return ""

    @staticmethod
    def _normalize_filter(filter_value: str, options: list[dict[str, str]]) -> str:
        normalized_input = (filter_value or "").strip().casefold()
        for option in options:
            if str(option.get("value", "")).casefold() == normalized_input:
                return str(option["value"])
        return str(options[0]["value"]) if options else "all"

    @staticmethod
    def _to_active_only(filter_value: str) -> bool | None:
        if filter_value == "active":
            return True
        if filter_value == "inactive":
            return False
        return None

    @staticmethod
    def _require_text(payload: dict[str, Any], key: str, message: str) -> str:
        value = str(payload.get(key, "") or "").strip()
        if not value:
            raise ValueError(message)
        return value

    @staticmethod
    def _optional_text(payload: dict[str, Any], key: str) -> str | None:
        value = str(payload.get(key, "") or "").strip()
        return value or None

    @staticmethod
    def _require_int(payload: dict[str, Any], key: str, message: str) -> int:
        value = payload.get(key, None)
        if value in (None, ""):
            raise ValueError(message)
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(message) from exc

    @staticmethod
    def _optional_int(payload: dict[str, Any], key: str) -> int | None:
        value = payload.get(key, None)
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{key} must be a whole number.") from exc

    @staticmethod
    def _optional_bool(payload: dict[str, Any], key: str, default: bool) -> bool:
        value = payload.get(key, default)
        if isinstance(value, bool):
            return value
        if value in (None, ""):
            return default
        if isinstance(value, str):
            normalized = value.strip().casefold()
            if normalized in {"true", "1", "yes", "on"}:
                return True
            if normalized in {"false", "0", "no", "off"}:
                return False
        return bool(value)

    @staticmethod
    def _optional_optional_bool(payload: dict[str, Any], key: str) -> bool | None:
        if key not in payload or payload.get(key, None) is None:
            return None
        return MaintenancePreventiveWorkspacePresenter._optional_bool(payload, key, False)


__all__ = ["MaintenancePreventiveWorkspacePresenter"]
