from __future__ import annotations

from collections import Counter

from src.core.modules.maintenance.api.desktop._support import (
    clean_text,
    decimal_value,
    format_enum_label,
)
from src.core.modules.maintenance.api.desktop.preventive.models import (
    MaintenancePreventiveChoiceDescriptor,
    MaintenancePreventiveForecastRowDescriptor,
    MaintenancePreventiveGenerationResultDescriptor,
    MaintenancePreventivePlanCreateCommand,
    MaintenancePreventivePlanDesktopDto,
    MaintenancePreventivePlanTaskCreateCommand,
    MaintenancePreventivePlanTaskDesktopDto,
    MaintenancePreventivePlanTaskUpdateCommand,
    MaintenancePreventivePlanUpdateCommand,
    MaintenancePreventiveQueueRowDescriptor,
    MaintenanceTaskStepTemplateCreateCommand,
    MaintenanceTaskStepTemplateDesktopDto,
    MaintenanceTaskStepTemplateUpdateCommand,
    MaintenanceTaskTemplateCreateCommand,
    MaintenanceTaskTemplateDesktopDto,
    MaintenanceTaskTemplateUpdateCommand,
)
from src.core.modules.maintenance.api.desktop.preventive.serializers import (
    serialize_forecast_row,
    serialize_generation_result,
    serialize_preventive_plan,
    serialize_preventive_plan_task,
    serialize_queue_row,
    serialize_task_step_template,
    serialize_task_template,
)
from src.core.modules.maintenance.api.desktop.shared_options import (
    MaintenanceAssetOptionDescriptor,
    MaintenanceComponentOptionDescriptor,
    MaintenanceSiteOptionDescriptor,
    MaintenanceSystemOptionDescriptor,
    serialize_asset_option,
    serialize_component_option,
    serialize_site_option,
    serialize_system_option,
)
from src.core.modules.maintenance.application.preventive.services.generation_service import (
    MaintenancePreventiveGenerationService,
)
from src.core.modules.maintenance.application.preventive.services.plan_service import (
    MaintenancePreventivePlanService,
)
from src.core.modules.maintenance.application.preventive.services.plan_task_service import (
    MaintenancePreventivePlanTaskService,
)
from src.core.modules.maintenance.application.preventive.services.task_step_template_service import (
    MaintenanceTaskStepTemplateService,
)
from src.core.modules.maintenance.application.preventive.services.task_template_service import (
    MaintenanceTaskTemplateService,
)
from src.core.modules.maintenance.application.reliability.sensor_service import (
    MaintenanceSensorService,
)
from src.core.modules.maintenance.application.assets.asset_service import (
    MaintenanceAssetService,
)
from src.core.modules.maintenance.application.assets.component_service import (
    MaintenanceAssetComponentService,
)
from src.core.modules.maintenance.application.assets.system_service import (
    MaintenanceSystemService,
)
from src.core.modules.maintenance.domain import (
    MaintenanceCalendarFrequencyUnit,
    MaintenanceGenerationLeadUnit,
    MaintenancePlanStatus,
    MaintenancePlanTaskTriggerScope,
    MaintenancePlanType,
    MaintenancePriority,
    MaintenanceSchedulePolicy,
    MaintenanceSensorDirection,
    MaintenanceTemplateStatus,
    MaintenanceTriggerMode,
)
from src.core.platform.org import SiteService


class MaintenancePreventiveDesktopApi:
    def __init__(
        self,
        *,
        site_service: SiteService | None = None,
        asset_service: MaintenanceAssetService | None = None,
        component_service: MaintenanceAssetComponentService | None = None,
        system_service: MaintenanceSystemService | None = None,
        sensor_service: MaintenanceSensorService | None = None,
        task_template_service: MaintenanceTaskTemplateService | None = None,
        task_step_template_service: MaintenanceTaskStepTemplateService | None = None,
        preventive_plan_service: MaintenancePreventivePlanService | None = None,
        preventive_plan_task_service: MaintenancePreventivePlanTaskService | None = None,
        preventive_generation_service: MaintenancePreventiveGenerationService | None = None,
    ) -> None:
        self._site_service = site_service
        self._asset_service = asset_service
        self._component_service = component_service
        self._system_service = system_service
        self._sensor_service = sensor_service
        self._task_template_service = task_template_service
        self._task_step_template_service = task_step_template_service
        self._preventive_plan_service = preventive_plan_service
        self._preventive_plan_task_service = preventive_plan_task_service
        self._preventive_generation_service = preventive_generation_service

    def list_sites(
        self,
        *,
        active_only: bool | None = None,
    ) -> tuple[MaintenanceSiteOptionDescriptor, ...]:
        if self._site_service is None:
            return ()
        return tuple(
            serialize_site_option(row)
            for row in self._site_service.list_sites(active_only=active_only)
        )

    def list_asset_options(
        self,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
        system_id: str | None = None,
    ) -> tuple[MaintenanceAssetOptionDescriptor, ...]:
        if self._asset_service is None:
            return ()
        return tuple(
            serialize_asset_option(row)
            for row in self._asset_service.list_assets(
                active_only=active_only,
                site_id=site_id,
                system_id=system_id,
            )
        )

    def list_component_options(
        self,
        *,
        active_only: bool | None = None,
        asset_id: str | None = None,
    ) -> tuple[MaintenanceComponentOptionDescriptor, ...]:
        if self._component_service is None:
            return ()
        return tuple(
            serialize_component_option(row)
            for row in self._component_service.list_components(
                active_only=active_only,
                asset_id=asset_id,
            )
        )

    def list_system_options(
        self,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
    ) -> tuple[MaintenanceSystemOptionDescriptor, ...]:
        if self._system_service is None:
            return ()
        return tuple(
            serialize_system_option(row)
            for row in self._system_service.list_systems(
                active_only=active_only,
                site_id=site_id,
            )
        )

    def list_sensor_options(
        self,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
    ) -> tuple[MaintenancePreventiveChoiceDescriptor, ...]:
        if self._sensor_service is None:
            return ()
        rows = self._sensor_service.list_sensors(
            active_only=active_only,
            site_id=site_id,
            asset_id=asset_id,
            component_id=component_id,
            system_id=system_id,
        )
        return tuple(
            MaintenancePreventiveChoiceDescriptor(
                value=row.id,
                label=clean_text(
                    f"{getattr(row, 'sensor_code', '')} - {getattr(row, 'sensor_name', '')}"
                ).strip(" -")
                or getattr(row, "sensor_name", "")
                or row.id,
            )
            for row in rows
        )

    def list_due_states(self) -> tuple[MaintenancePreventiveChoiceDescriptor, ...]:
        return (
            MaintenancePreventiveChoiceDescriptor("DUE", "Due"),
            MaintenancePreventiveChoiceDescriptor("DUE_SOON", "Due Soon"),
            MaintenancePreventiveChoiceDescriptor("BLOCKED", "Blocked"),
            MaintenancePreventiveChoiceDescriptor("NOT_DUE", "Not Due"),
            MaintenancePreventiveChoiceDescriptor("INACTIVE", "Inactive"),
        )

    def list_plan_statuses(self) -> tuple[MaintenancePreventiveChoiceDescriptor, ...]:
        return tuple(
            MaintenancePreventiveChoiceDescriptor(
                value=status.value,
                label=format_enum_label(status.value),
            )
            for status in MaintenancePlanStatus
        )

    def list_plan_types(self) -> tuple[MaintenancePreventiveChoiceDescriptor, ...]:
        return tuple(
            MaintenancePreventiveChoiceDescriptor(
                value=plan_type.value,
                label=format_enum_label(plan_type.value),
            )
            for plan_type in MaintenancePlanType
        )

    def list_priorities(self) -> tuple[MaintenancePreventiveChoiceDescriptor, ...]:
        return tuple(
            MaintenancePreventiveChoiceDescriptor(
                value=priority.value,
                label=format_enum_label(priority.value),
            )
            for priority in MaintenancePriority
        )

    def list_trigger_modes(self) -> tuple[MaintenancePreventiveChoiceDescriptor, ...]:
        return tuple(
            MaintenancePreventiveChoiceDescriptor(
                value=mode.value,
                label=format_enum_label(mode.value),
            )
            for mode in MaintenanceTriggerMode
        )

    def list_schedule_policies(self) -> tuple[MaintenancePreventiveChoiceDescriptor, ...]:
        return tuple(
            MaintenancePreventiveChoiceDescriptor(
                value=policy.value,
                label=format_enum_label(policy.value),
            )
            for policy in MaintenanceSchedulePolicy
        )

    def list_calendar_frequency_units(
        self,
    ) -> tuple[MaintenancePreventiveChoiceDescriptor, ...]:
        return tuple(
            MaintenancePreventiveChoiceDescriptor(
                value=unit.value,
                label=format_enum_label(unit.value),
            )
            for unit in MaintenanceCalendarFrequencyUnit
        )

    def list_generation_lead_units(
        self,
    ) -> tuple[MaintenancePreventiveChoiceDescriptor, ...]:
        return tuple(
            MaintenancePreventiveChoiceDescriptor(
                value=unit.value,
                label=format_enum_label(unit.value),
            )
            for unit in MaintenanceGenerationLeadUnit
        )

    def list_sensor_directions(
        self,
    ) -> tuple[MaintenancePreventiveChoiceDescriptor, ...]:
        return tuple(
            MaintenancePreventiveChoiceDescriptor(
                value=direction.value,
                label=format_enum_label(direction.value),
            )
            for direction in MaintenanceSensorDirection
        )

    def list_plan_task_trigger_scopes(
        self,
    ) -> tuple[MaintenancePreventiveChoiceDescriptor, ...]:
        return tuple(
            MaintenancePreventiveChoiceDescriptor(
                value=scope.value,
                label=format_enum_label(scope.value),
            )
            for scope in MaintenancePlanTaskTriggerScope
        )

    def list_task_template_statuses(
        self,
    ) -> tuple[MaintenancePreventiveChoiceDescriptor, ...]:
        return tuple(
            MaintenancePreventiveChoiceDescriptor(
                value=status.value,
                label=format_enum_label(status.value),
            )
            for status in MaintenanceTemplateStatus
        )

    def list_task_template_maintenance_types(
        self,
        *,
        active_only: bool | None = None,
    ) -> tuple[MaintenancePreventiveChoiceDescriptor, ...]:
        rows = self.list_task_templates(active_only=active_only)
        values = sorted(
            {
                row.maintenance_type
                for row in rows
                if clean_text(row.maintenance_type)
            }
        )
        return tuple(
            MaintenancePreventiveChoiceDescriptor(
                value=value,
                label=format_enum_label(value),
            )
            for value in values
        )

    def list_task_templates(
        self,
        *,
        active_only: bool | None = None,
        maintenance_type: str | None = None,
        template_status: str | None = None,
        search_text: str = "",
    ) -> tuple[MaintenanceTaskTemplateDesktopDto, ...]:
        if self._task_template_service is None:
            return ()
        rows = self._task_template_service.search_task_templates(
            search_text=search_text,
            active_only=active_only,
            maintenance_type=maintenance_type,
            template_status=template_status,
        )
        step_count_lookup = Counter()
        if self._task_step_template_service is not None:
            for step in self._task_step_template_service.list_step_templates(
                active_only=None
            ):
                step_count_lookup[step.task_template_id] += 1
        return tuple(
            serialize_task_template(
                row,
                step_count=step_count_lookup.get(row.id, 0),
            )
            for row in rows
        )

    def get_task_template(
        self,
        task_template_id: str,
    ) -> MaintenanceTaskTemplateDesktopDto:
        self._require_service(self._task_template_service, "task template service")
        row = self._task_template_service.get_task_template(task_template_id)
        step_count = 0
        if self._task_step_template_service is not None:
            step_count = len(
                self._task_step_template_service.list_step_templates(
                    task_template_id=row.id,
                    active_only=None,
                )
            )
        return serialize_task_template(row, step_count=step_count)

    def list_task_step_templates(
        self,
        *,
        task_template_id: str,
        active_only: bool | None = None,
    ) -> tuple[MaintenanceTaskStepTemplateDesktopDto, ...]:
        if self._task_step_template_service is None:
            return ()
        rows = self._task_step_template_service.list_step_templates(
            task_template_id=task_template_id,
            active_only=active_only,
        )
        return tuple(serialize_task_step_template(row) for row in rows)

    def create_task_template(
        self,
        command: MaintenanceTaskTemplateCreateCommand,
    ) -> MaintenanceTaskTemplateDesktopDto:
        self._require_service(self._task_template_service, "task template service")
        row = self._task_template_service.create_task_template(
            task_template_code=command.task_template_code,
            name=command.name,
            description=command.description,
            maintenance_type=command.maintenance_type,
            revision_no=command.revision_no,
            template_status=command.template_status,
            estimated_minutes=command.estimated_minutes,
            required_skill=command.required_skill,
            requires_shutdown=command.requires_shutdown,
            requires_permit=command.requires_permit,
            is_active=command.is_active,
            notes=command.notes,
        )
        return serialize_task_template(row, step_count=0)

    def update_task_template(
        self,
        command: MaintenanceTaskTemplateUpdateCommand,
    ) -> MaintenanceTaskTemplateDesktopDto:
        self._require_service(self._task_template_service, "task template service")
        row = self._task_template_service.update_task_template(
            command.task_template_id,
            task_template_code=command.task_template_code,
            name=command.name,
            description=command.description,
            maintenance_type=command.maintenance_type,
            revision_no=command.revision_no,
            template_status=command.template_status,
            estimated_minutes=command.estimated_minutes,
            required_skill=command.required_skill,
            requires_shutdown=command.requires_shutdown,
            requires_permit=command.requires_permit,
            is_active=command.is_active,
            notes=command.notes,
            expected_version=command.expected_version,
        )
        step_count = 0
        if self._task_step_template_service is not None:
            step_count = len(
                self._task_step_template_service.list_step_templates(
                    task_template_id=row.id,
                    active_only=None,
                )
            )
        return serialize_task_template(row, step_count=step_count)

    def create_task_step_template(
        self,
        command: MaintenanceTaskStepTemplateCreateCommand,
    ) -> MaintenanceTaskStepTemplateDesktopDto:
        self._require_service(
            self._task_step_template_service,
            "task step template service",
        )
        row = self._task_step_template_service.create_step_template(
            task_template_id=command.task_template_id,
            step_number=command.step_number,
            sort_order=command.sort_order,
            instruction=command.instruction,
            expected_result=command.expected_result,
            hint_level=command.hint_level,
            hint_text=command.hint_text,
            requires_confirmation=command.requires_confirmation,
            requires_measurement=command.requires_measurement,
            requires_photo=command.requires_photo,
            measurement_unit=command.measurement_unit,
            is_active=command.is_active,
            notes=command.notes,
        )
        return serialize_task_step_template(row)

    def update_task_step_template(
        self,
        command: MaintenanceTaskStepTemplateUpdateCommand,
    ) -> MaintenanceTaskStepTemplateDesktopDto:
        self._require_service(
            self._task_step_template_service,
            "task step template service",
        )
        row = self._task_step_template_service.update_step_template(
            command.task_step_template_id,
            step_number=command.step_number,
            sort_order=command.sort_order,
            instruction=command.instruction,
            expected_result=command.expected_result,
            hint_level=command.hint_level,
            hint_text=command.hint_text,
            requires_confirmation=command.requires_confirmation,
            requires_measurement=command.requires_measurement,
            requires_photo=command.requires_photo,
            measurement_unit=command.measurement_unit,
            is_active=command.is_active,
            notes=command.notes,
            expected_version=command.expected_version,
        )
        return serialize_task_step_template(row)

    def list_preventive_plans(
        self,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        status: str | None = None,
        plan_type: str | None = None,
        trigger_mode: str | None = None,
        search_text: str = "",
    ) -> tuple[MaintenancePreventivePlanDesktopDto, ...]:
        if self._preventive_plan_service is None:
            return ()
        rows = self._preventive_plan_service.search_preventive_plans(
            search_text=search_text,
            active_only=active_only,
            site_id=site_id,
            asset_id=asset_id,
            component_id=component_id,
            system_id=system_id,
            status=status,
            plan_type=plan_type,
            trigger_mode=trigger_mode,
        )
        return tuple(self._serialize_plan(row) for row in rows)

    def get_preventive_plan(
        self,
        plan_id: str,
    ) -> MaintenancePreventivePlanDesktopDto:
        self._require_service(self._preventive_plan_service, "preventive plan service")
        row = self._preventive_plan_service.get_preventive_plan(plan_id)
        return self._serialize_plan(row)

    def list_plan_tasks(
        self,
        *,
        plan_id: str,
    ) -> tuple[MaintenancePreventivePlanTaskDesktopDto, ...]:
        if self._preventive_plan_task_service is None:
            return ()
        task_template_lookup = self._task_template_label_lookup()
        sensor_lookup = self._sensor_label_lookup()
        rows = self._preventive_plan_task_service.list_plan_tasks(plan_id=plan_id)
        rows = sorted(rows, key=lambda row: (row.sequence_no, row.id))
        return tuple(
            serialize_preventive_plan_task(
                row,
                task_template_lookup=task_template_lookup,
                sensor_lookup=sensor_lookup,
            )
            for row in rows
        )

    def create_preventive_plan(
        self,
        command: MaintenancePreventivePlanCreateCommand,
    ) -> MaintenancePreventivePlanDesktopDto:
        self._require_service(self._preventive_plan_service, "preventive plan service")
        row = self._preventive_plan_service.create_preventive_plan(
            site_id=command.site_id,
            plan_code=command.plan_code,
            name=command.name,
            asset_id=command.asset_id,
            component_id=command.component_id,
            system_id=command.system_id,
            description=command.description,
            status=command.status,
            plan_type=command.plan_type,
            priority=command.priority,
            trigger_mode=command.trigger_mode,
            schedule_policy=command.schedule_policy,
            calendar_frequency_unit=command.calendar_frequency_unit,
            calendar_frequency_value=command.calendar_frequency_value,
            generation_horizon_count=command.generation_horizon_count,
            generation_lead_value=command.generation_lead_value,
            generation_lead_unit=command.generation_lead_unit,
            sensor_id=command.sensor_id,
            sensor_threshold=decimal_value(command.sensor_threshold),
            sensor_direction=command.sensor_direction,
            sensor_reset_rule=command.sensor_reset_rule,
            requires_shutdown=command.requires_shutdown,
            approval_required=command.approval_required,
            auto_generate_work_order=command.auto_generate_work_order,
            is_active=command.is_active,
            notes=command.notes,
        )
        return self._serialize_plan(row)

    def update_preventive_plan(
        self,
        command: MaintenancePreventivePlanUpdateCommand,
    ) -> MaintenancePreventivePlanDesktopDto:
        self._require_service(self._preventive_plan_service, "preventive plan service")
        row = self._preventive_plan_service.update_preventive_plan(
            command.plan_id,
            site_id=command.site_id,
            plan_code=command.plan_code,
            name=command.name,
            asset_id=command.asset_id,
            component_id=command.component_id,
            system_id=command.system_id,
            description=command.description,
            status=command.status,
            plan_type=command.plan_type,
            priority=command.priority,
            trigger_mode=command.trigger_mode,
            schedule_policy=command.schedule_policy,
            calendar_frequency_unit=command.calendar_frequency_unit,
            calendar_frequency_value=command.calendar_frequency_value,
            generation_horizon_count=command.generation_horizon_count,
            generation_lead_value=command.generation_lead_value,
            generation_lead_unit=command.generation_lead_unit,
            sensor_id=command.sensor_id,
            sensor_threshold=decimal_value(command.sensor_threshold),
            sensor_direction=command.sensor_direction,
            sensor_reset_rule=command.sensor_reset_rule,
            requires_shutdown=command.requires_shutdown,
            approval_required=command.approval_required,
            auto_generate_work_order=command.auto_generate_work_order,
            is_active=command.is_active,
            notes=command.notes,
            expected_version=command.expected_version,
        )
        return self._serialize_plan(row)

    def create_plan_task(
        self,
        command: MaintenancePreventivePlanTaskCreateCommand,
    ) -> MaintenancePreventivePlanTaskDesktopDto:
        self._require_service(
            self._preventive_plan_task_service,
            "preventive plan task service",
        )
        row = self._preventive_plan_task_service.create_plan_task(
            plan_id=command.plan_id,
            task_template_id=command.task_template_id,
            trigger_scope=command.trigger_scope,
            trigger_mode_override=command.trigger_mode_override,
            calendar_frequency_unit_override=command.calendar_frequency_unit_override,
            calendar_frequency_value_override=command.calendar_frequency_value_override,
            sensor_id_override=command.sensor_id_override,
            sensor_threshold_override=decimal_value(command.sensor_threshold_override),
            sensor_direction_override=command.sensor_direction_override,
            sequence_no=command.sequence_no,
            is_mandatory=command.is_mandatory,
            default_assigned_team_id=command.default_assigned_team_id,
            estimated_minutes_override=command.estimated_minutes_override,
            notes=command.notes,
        )
        return serialize_preventive_plan_task(
            row,
            task_template_lookup=self._task_template_label_lookup(),
            sensor_lookup=self._sensor_label_lookup(),
        )

    def update_plan_task(
        self,
        command: MaintenancePreventivePlanTaskUpdateCommand,
    ) -> MaintenancePreventivePlanTaskDesktopDto:
        self._require_service(
            self._preventive_plan_task_service,
            "preventive plan task service",
        )
        row = self._preventive_plan_task_service.update_plan_task(
            command.plan_task_id,
            task_template_id=command.task_template_id,
            trigger_scope=command.trigger_scope,
            trigger_mode_override=command.trigger_mode_override,
            calendar_frequency_unit_override=command.calendar_frequency_unit_override,
            calendar_frequency_value_override=command.calendar_frequency_value_override,
            sensor_id_override=command.sensor_id_override,
            sensor_threshold_override=decimal_value(command.sensor_threshold_override),
            sensor_direction_override=command.sensor_direction_override,
            sequence_no=command.sequence_no,
            is_mandatory=command.is_mandatory,
            default_assigned_team_id=command.default_assigned_team_id,
            estimated_minutes_override=command.estimated_minutes_override,
            notes=command.notes,
            expected_version=command.expected_version,
        )
        return serialize_preventive_plan_task(
            row,
            task_template_lookup=self._task_template_label_lookup(),
            sensor_lookup=self._sensor_label_lookup(),
        )

    def list_due_candidates(
        self,
        *,
        site_id: str | None = None,
        plan_id: str | None = None,
    ) -> tuple[MaintenancePreventiveQueueRowDescriptor, ...]:
        if self._preventive_generation_service is None or self._preventive_plan_service is None:
            return ()
        candidates = self._preventive_generation_service.list_due_candidates(
            site_id=site_id,
            plan_id=plan_id,
        )
        plan_lookup = {
            row.id: row
            for row in self._preventive_plan_service.list_preventive_plans(
                active_only=None,
                site_id=site_id,
            )
        }
        site_lookup = self._site_label_lookup()
        asset_lookup = self._asset_label_lookup()
        component_lookup = self._component_label_lookup()
        system_lookup = self._system_label_lookup()
        sensor_lookup = self._sensor_label_lookup()
        rows: list[MaintenancePreventiveQueueRowDescriptor] = []
        for candidate in candidates:
            plan = plan_lookup.get(candidate.plan_id)
            if plan is None:
                continue
            rows.append(
                serialize_queue_row(
                    plan,
                    candidate,
                    site_lookup=site_lookup,
                    asset_lookup=asset_lookup,
                    component_lookup=component_lookup,
                    system_lookup=system_lookup,
                    sensor_lookup=sensor_lookup,
                )
            )
        return tuple(rows)

    def preview_plan_schedule(
        self,
        *,
        plan_id: str,
    ) -> tuple[MaintenancePreventiveForecastRowDescriptor, ...]:
        if self._preventive_generation_service is None:
            return ()
        rows = self._preventive_generation_service.preview_plan_schedule(plan_id=plan_id)
        return tuple(serialize_forecast_row(row) for row in rows)

    def regenerate_plan_schedule(
        self,
        *,
        plan_id: str,
    ) -> tuple[MaintenancePreventiveForecastRowDescriptor, ...]:
        self._require_service(
            self._preventive_generation_service,
            "preventive generation service",
        )
        rows = self._preventive_generation_service.regenerate_plan_schedule(
            plan_id=plan_id
        )
        return tuple(serialize_forecast_row(row) for row in rows)

    def generate_due_work(
        self,
        *,
        plan_id: str,
    ) -> tuple[MaintenancePreventiveGenerationResultDescriptor, ...]:
        self._require_service(
            self._preventive_generation_service,
            "preventive generation service",
        )
        rows = self._preventive_generation_service.generate_due_work(plan_id=plan_id)
        return tuple(serialize_generation_result(row) for row in rows)

    def _serialize_plan(self, row) -> MaintenancePreventivePlanDesktopDto:
        plan_task_count_lookup = Counter()
        if self._preventive_plan_task_service is not None:
            for plan_task in self._preventive_plan_task_service.list_plan_tasks():
                plan_task_count_lookup[plan_task.plan_id] += 1
        return serialize_preventive_plan(
            row,
            site_lookup=self._site_label_lookup(),
            asset_lookup=self._asset_label_lookup(),
            component_lookup=self._component_label_lookup(),
            system_lookup=self._system_label_lookup(),
            sensor_lookup=self._sensor_label_lookup(),
            plan_task_count=plan_task_count_lookup.get(row.id, 0),
        )

    def _site_label_lookup(self) -> dict[str, str]:
        return {
            row.value: row.label
            for row in self.list_sites(active_only=None)
        }

    def _asset_label_lookup(self) -> dict[str, str]:
        return {
            row.value: row.label
            for row in self.list_asset_options(active_only=None)
        }

    def _component_label_lookup(self) -> dict[str, str]:
        return {
            row.value: row.label
            for row in self.list_component_options(active_only=None)
        }

    def _system_label_lookup(self) -> dict[str, str]:
        return {
            row.value: row.label
            for row in self.list_system_options(active_only=None)
        }

    def _sensor_label_lookup(self) -> dict[str, str]:
        return {
            row.value: row.label
            for row in self.list_sensor_options(active_only=None)
        }

    def _task_template_label_lookup(self) -> dict[str, str]:
        return {
            row.id: f"{row.task_template_code} - {row.name}"
            for row in self.list_task_templates(active_only=None)
        }

    @staticmethod
    def _require_service(service, label: str) -> None:
        if service is None:
            raise RuntimeError(f"Maintenance {label} is not configured.")


def build_maintenance_preventive_desktop_api(
    *,
    site_service: SiteService | None = None,
    asset_service: MaintenanceAssetService | None = None,
    component_service: MaintenanceAssetComponentService | None = None,
    system_service: MaintenanceSystemService | None = None,
    sensor_service: MaintenanceSensorService | None = None,
    task_template_service: MaintenanceTaskTemplateService | None = None,
    task_step_template_service: MaintenanceTaskStepTemplateService | None = None,
    preventive_plan_service: MaintenancePreventivePlanService | None = None,
    preventive_plan_task_service: MaintenancePreventivePlanTaskService | None = None,
    preventive_generation_service: MaintenancePreventiveGenerationService | None = None,
) -> MaintenancePreventiveDesktopApi:
    return MaintenancePreventiveDesktopApi(
        site_service=site_service,
        asset_service=asset_service,
        component_service=component_service,
        system_service=system_service,
        sensor_service=sensor_service,
        task_template_service=task_template_service,
        task_step_template_service=task_step_template_service,
        preventive_plan_service=preventive_plan_service,
        preventive_plan_task_service=preventive_plan_task_service,
        preventive_generation_service=preventive_generation_service,
    )


__all__ = [
    "MaintenancePreventiveDesktopApi",
    "build_maintenance_preventive_desktop_api",
]
