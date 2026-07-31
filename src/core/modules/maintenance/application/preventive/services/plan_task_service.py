from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.maintenance.domain import (
    MaintenancePlanTaskTriggerScope,
    MaintenancePreventivePlan,
    MaintenancePreventivePlanTask,
    MaintenanceSensor,
    MaintenanceTriggerMode,
)
from src.core.modules.maintenance.contracts.repositories import (
    MaintenanceAssetComponentRepository,
    MaintenancePreventivePlanRepository,
    MaintenancePreventivePlanTaskRepository,
    MaintenanceSensorRepository,
    MaintenanceTaskTemplateRepository,
)
from src.core.modules.maintenance.application.common.support import normalize_optional_text
from src.core.modules.maintenance.application.common.scope_authorization import (
    deny_maintenance_scope_access,
)
from src.core.platform.access.authorization import filter_scope_rows, require_scope_permission
from src.core.shared.activity.activity_recorder import record_activity
from src.core.platform.auth.authorization import require_permission
from src.core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.org.contracts import OrganizationRepository
from src.core.platform.tenancy.tenant_context import (
    TenantContextService,
    require_tenant_context_service,
)
from src.core.shared.events.domain_events import DomainChangeEvent, domain_events
from src.core.platform.org.domain import Organization


class MaintenancePreventivePlanTaskService:
    def __init__(
        self,
        session: Session,
        preventive_plan_task_repo: MaintenancePreventivePlanTaskRepository,
        *,
        organization_repo: OrganizationRepository,
        preventive_plan_repo: MaintenancePreventivePlanRepository,
        task_template_repo: MaintenanceTaskTemplateRepository,
        sensor_repo: MaintenanceSensorRepository,
        component_repo: MaintenanceAssetComponentRepository,
        tenant_context_service: TenantContextService | None = None,
        user_session=None,
        activity_service=None,
    ) -> None:
        self._session = session
        self._preventive_plan_task_repo = preventive_plan_task_repo
        self._organization_repo = organization_repo
        self._tenant_context_service = require_tenant_context_service(
            tenant_context_service,
            consumer_label="MaintenancePreventivePlanTaskService",
        )
        self._preventive_plan_repo = preventive_plan_repo
        self._task_template_repo = task_template_repo
        self._sensor_repo = sensor_repo
        self._component_repo = component_repo
        self._user_session = user_session
        self._activity_service = activity_service

    def list_plan_tasks(
        self,
        *,
        plan_id: str | None = None,
        task_template_id: str | None = None,
    ) -> list[MaintenancePreventivePlanTask]:
        self._require_read("list maintenance preventive plan tasks")
        organization = self._active_organization()
        if plan_id is not None:
            self._get_plan(plan_id, organization=organization)
        rows = self._preventive_plan_task_repo.list_for_organization(
            organization.id,
            plan_id=normalize_optional_text(plan_id) or None,
            task_template_id=normalize_optional_text(task_template_id) or None,
        )
        return filter_scope_rows(
            rows,
            self._user_session,
            scope_type="maintenance",
            permission_code="maintenance.read",
            scope_id_getter=self._scope_anchor_for_task,
        )

    def get_plan_task(self, preventive_plan_task_id: str) -> MaintenancePreventivePlanTask:
        self._require_read("view maintenance preventive plan task")
        organization = self._active_organization()
        row = self._get_plan_task(preventive_plan_task_id, organization=organization)
        self._require_scope_read(
            self._scope_anchor_for_task(row),
            operation_label="view maintenance preventive plan task",
        )
        return row

    def create_plan_task(
        self,
        *,
        plan_id: str,
        task_template_id: str,
        trigger_scope=None,
        trigger_mode_override=None,
        calendar_frequency_unit_override=None,
        calendar_frequency_value_override: int | str | None = None,
        sensor_id_override: str | None = None,
        sensor_threshold_override: Decimal | int | float | str | None = None,
        sensor_direction_override=None,
        sequence_no: int | str | None = None,
        is_mandatory: bool = True,
        default_assigned_employee_id: str | None = None,
        default_assigned_team_id: str | None = None,
        estimated_minutes_override: int | str | None = None,
        notes: str = "",
    ) -> MaintenancePreventivePlanTask:
        self._require_manage("create maintenance preventive plan task")
        organization = self._active_organization()
        plan = self._get_plan(plan_id, organization=organization)
        self._require_scope_manage(
            self._scope_anchor_for_plan(plan),
            operation_label="create maintenance preventive plan task",
        )
        task_template = self._get_task_template(task_template_id, organization=organization)
        row = MaintenancePreventivePlanTask.create(
            organization_id=organization.id,
            plan_id=plan.id,
            task_template_id=task_template.id,
            trigger_scope=trigger_scope,
            trigger_mode_override=trigger_mode_override,
            calendar_frequency_unit_override=calendar_frequency_unit_override,
            calendar_frequency_value_override=calendar_frequency_value_override,
            sensor_id_override=sensor_id_override,
            sensor_threshold_override=sensor_threshold_override,
            sensor_direction_override=sensor_direction_override,
            sequence_no=self._resolve_sequence_no(plan.id, sequence_no),
            is_mandatory=bool(is_mandatory),
            default_assigned_employee_id=default_assigned_employee_id,
            default_assigned_team_id=default_assigned_team_id,
            estimated_minutes_override=estimated_minutes_override,
            notes=notes,
        )
        self._ensure_unique_sequence(organization.id, plan_id=plan.id, sequence_no=row.sequence_no)
        self._validate_override_configuration(
            organization=organization,
            plan=plan,
            row=row,
        )
        try:
            self._preventive_plan_task_repo.add(row)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Preventive plan task could not be saved.",
                code="MAINTENANCE_PREVENTIVE_PLAN_TASK_SAVE_FAILED",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_preventive_plan_task.create", row)
        return row

    def update_plan_task(
        self,
        preventive_plan_task_id: str,
        *,
        task_template_id: str | None = None,
        trigger_scope=None,
        trigger_mode_override=None,
        calendar_frequency_unit_override=None,
        calendar_frequency_value_override: int | str | None = None,
        sensor_id_override: str | None = None,
        sensor_threshold_override: Decimal | int | float | str | None = None,
        sensor_direction_override=None,
        sequence_no: int | str | None = None,
        is_mandatory: bool | None = None,
        default_assigned_employee_id: str | None = None,
        default_assigned_team_id: str | None = None,
        estimated_minutes_override: int | str | None = None,
        notes: str | None = None,
        expected_version: int | None = None,
    ) -> MaintenancePreventivePlanTask:
        self._require_manage("update maintenance preventive plan task")
        organization = self._active_organization()
        row = self.get_plan_task(preventive_plan_task_id)
        plan = self._get_plan(row.plan_id, organization=organization)
        self._require_scope_manage(
            self._scope_anchor_for_plan(plan),
            operation_label="update maintenance preventive plan task",
        )
        if expected_version is not None and row.version != expected_version:
            raise ConcurrencyError(
                "Maintenance preventive plan task changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        target_trigger_scope = row.trigger_scope if trigger_scope is None else trigger_scope
        clear_overrides = self._is_inherit_plan_scope(target_trigger_scope)
        updated = replace(
            row,
            task_template_id=(
                row.task_template_id
                if task_template_id is None
                else self._get_task_template(task_template_id, organization=organization).id
            ),
            trigger_scope=target_trigger_scope,
            trigger_mode_override=(
                None
                if clear_overrides
                else (
                    row.trigger_mode_override
                    if trigger_mode_override is None
                    else trigger_mode_override
                )
            ),
            calendar_frequency_unit_override=(
                None
                if clear_overrides
                else (
                    row.calendar_frequency_unit_override
                    if calendar_frequency_unit_override is None
                    else calendar_frequency_unit_override
                )
            ),
            calendar_frequency_value_override=(
                None
                if clear_overrides
                else (
                    row.calendar_frequency_value_override
                    if calendar_frequency_value_override is None
                    else calendar_frequency_value_override
                )
            ),
            sensor_id_override=(
                None
                if clear_overrides
                else (row.sensor_id_override if sensor_id_override is None else sensor_id_override)
            ),
            sensor_threshold_override=(
                None
                if clear_overrides
                else (
                    row.sensor_threshold_override
                    if sensor_threshold_override is None
                    else sensor_threshold_override
                )
            ),
            sensor_direction_override=(
                None
                if clear_overrides
                else (
                    row.sensor_direction_override
                    if sensor_direction_override is None
                    else sensor_direction_override
                )
            ),
            sequence_no=(
                row.sequence_no if sequence_no is None else self._resolve_sequence_no(plan.id, sequence_no)
            ),
            is_mandatory=row.is_mandatory if is_mandatory is None else bool(is_mandatory),
            default_assigned_employee_id=(
                row.default_assigned_employee_id
                if default_assigned_employee_id is None
                else default_assigned_employee_id
            ),
            default_assigned_team_id=(
                row.default_assigned_team_id
                if default_assigned_team_id is None
                else default_assigned_team_id
            ),
            estimated_minutes_override=(
                row.estimated_minutes_override
                if estimated_minutes_override is None
                else estimated_minutes_override
            ),
            notes=row.notes if notes is None else notes,
            updated_at=datetime.now(timezone.utc),
        )
        self._ensure_unique_sequence(
            organization.id,
            plan_id=plan.id,
            sequence_no=updated.sequence_no,
            exclude_id=row.id,
        )
        self._validate_override_configuration(
            organization=organization,
            plan=plan,
            row=updated,
        )
        try:
            self._preventive_plan_task_repo.update(updated)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Preventive plan task could not be updated.",
                code="MAINTENANCE_PREVENTIVE_PLAN_TASK_SAVE_FAILED",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_preventive_plan_task.update", updated)
        return updated

    def _validate_override_configuration(
        self,
        *,
        organization: Organization,
        plan: MaintenancePreventivePlan,
        row: MaintenancePreventivePlanTask,
    ) -> None:
        if row.trigger_scope == MaintenancePlanTaskTriggerScope.INHERIT_PLAN:
            return
        sensor = self._resolve_override_sensor(
            organization=organization,
            plan=plan,
            sensor_id=row.sensor_id_override,
        )
        self._validate_override_trigger_configuration(
            trigger_mode=row.trigger_mode_override or MaintenanceTriggerMode.CALENDAR,
            calendar_frequency_unit=row.calendar_frequency_unit_override,
            calendar_frequency_value=row.calendar_frequency_value_override,
            sensor=sensor,
            sensor_threshold=row.sensor_threshold_override,
            sensor_direction=row.sensor_direction_override,
        )

    def _resolve_override_sensor(
        self,
        *,
        organization: Organization,
        plan: MaintenancePreventivePlan,
        sensor_id: str | None,
    ) -> MaintenanceSensor | None:
        if not sensor_id:
            return None
        sensor = self._sensor_repo.get(sensor_id)
        if sensor is None or sensor.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance sensor not found in the active organization.",
                code="MAINTENANCE_SENSOR_NOT_FOUND",
            )
        if sensor.site_id != plan.site_id:
            raise ValidationError(
                "Selected override sensor must belong to the preventive plan site.",
                code="MAINTENANCE_PREVENTIVE_PLAN_TASK_SENSOR_SITE_MISMATCH",
            )
        if plan.asset_id and sensor.asset_id not in (None, plan.asset_id):
            raise ValidationError(
                "Selected override sensor must align with the preventive plan asset context.",
                code="MAINTENANCE_PREVENTIVE_PLAN_TASK_SENSOR_CONTEXT_MISMATCH",
            )
        if plan.component_id and sensor.component_id not in (None, plan.component_id):
            raise ValidationError(
                "Selected override sensor must align with the preventive plan component context.",
                code="MAINTENANCE_PREVENTIVE_PLAN_TASK_SENSOR_CONTEXT_MISMATCH",
            )
        if plan.system_id and sensor.system_id not in (None, plan.system_id):
            raise ValidationError(
                "Selected override sensor must align with the preventive plan system context.",
                code="MAINTENANCE_PREVENTIVE_PLAN_TASK_SENSOR_CONTEXT_MISMATCH",
            )
        return sensor

    def _validate_override_trigger_configuration(
        self,
        *,
        trigger_mode: MaintenanceTriggerMode,
        calendar_frequency_unit,
        calendar_frequency_value: int | None,
        sensor: MaintenanceSensor | None,
        sensor_threshold: Decimal | None,
        sensor_direction,
    ) -> None:
        has_calendar = calendar_frequency_unit is not None and calendar_frequency_value not in (None, 0)
        has_sensor = sensor is not None and sensor_threshold is not None and sensor_direction is not None
        if trigger_mode == MaintenanceTriggerMode.CALENDAR:
            if not has_calendar:
                raise ValidationError(
                    "Calendar-triggered task overrides require frequency unit and value.",
                    code="MAINTENANCE_PREVENTIVE_PLAN_TASK_CALENDAR_REQUIRED",
                )
            if sensor is not None or sensor_threshold is not None or sensor_direction is not None:
                raise ValidationError(
                    "Calendar-triggered task overrides cannot define sensor fields.",
                    code="MAINTENANCE_PREVENTIVE_PLAN_TASK_SENSOR_NOT_ALLOWED",
                )
            return
        if trigger_mode == MaintenanceTriggerMode.SENSOR:
            if not has_sensor:
                raise ValidationError(
                    "Sensor-triggered task overrides require sensor, threshold, and direction.",
                    code="MAINTENANCE_PREVENTIVE_PLAN_TASK_SENSOR_REQUIRED",
                )
            if calendar_frequency_unit is not None or calendar_frequency_value is not None:
                raise ValidationError(
                    "Sensor-triggered task overrides cannot define calendar fields.",
                    code="MAINTENANCE_PREVENTIVE_PLAN_TASK_CALENDAR_NOT_ALLOWED",
                )
            return
        if not has_calendar:
            raise ValidationError(
                "Hybrid task overrides require frequency unit and value.",
                code="MAINTENANCE_PREVENTIVE_PLAN_TASK_CALENDAR_REQUIRED",
            )
        if not has_sensor:
            raise ValidationError(
                "Hybrid task overrides require sensor, threshold, and direction.",
                code="MAINTENANCE_PREVENTIVE_PLAN_TASK_SENSOR_REQUIRED",
            )

    def _resolve_sequence_no(self, plan_id: str, sequence_no: int | str | None) -> int | str:
        if sequence_no not in (None, ""):
            return sequence_no
        rows = self._preventive_plan_task_repo.list_for_organization(
            self._active_organization().id,
            plan_id=plan_id,
        )
        highest = max((row.sequence_no for row in rows), default=0)
        return highest + 1

    def _is_inherit_plan_scope(self, value: object) -> bool:
        if isinstance(value, MaintenancePlanTaskTriggerScope):
            return value == MaintenancePlanTaskTriggerScope.INHERIT_PLAN
        return (
            normalize_optional_text(value).upper()
            == MaintenancePlanTaskTriggerScope.INHERIT_PLAN.value
        )

    def _ensure_unique_sequence(
        self,
        organization_id: str,
        *,
        plan_id: str,
        sequence_no: int,
        exclude_id: str | None = None,
    ) -> None:
        rows = self._preventive_plan_task_repo.list_for_organization(organization_id, plan_id=plan_id)
        if any(row.sequence_no == sequence_no and row.id != exclude_id for row in rows):
            raise ValidationError(
                "Sequence number already exists on the selected preventive plan.",
                code="MAINTENANCE_PREVENTIVE_PLAN_TASK_SEQUENCE_EXISTS",
            )

    def _active_organization(self) -> Organization:
        return self._tenant_context_service.require_context(
            operation_label="maintenance preventive plan tasks"
        ).organization

    def _get_plan(self, plan_id: str, *, organization: Organization) -> MaintenancePreventivePlan:
        row = self._preventive_plan_repo.get(plan_id)
        if row is None or row.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance preventive plan not found in the active organization.",
                code="MAINTENANCE_PREVENTIVE_PLAN_NOT_FOUND",
            )
        return row

    def _get_task_template(self, task_template_id: str, *, organization: Organization):
        row = self._task_template_repo.get(task_template_id)
        if row is None or row.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance task template not found in the active organization.",
                code="MAINTENANCE_TASK_TEMPLATE_NOT_FOUND",
            )
        return row

    def _get_plan_task(self, preventive_plan_task_id: str, *, organization: Organization) -> MaintenancePreventivePlanTask:
        row = self._preventive_plan_task_repo.get(preventive_plan_task_id)
        if row is None or row.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance preventive plan task not found in the active organization.",
                code="MAINTENANCE_PREVENTIVE_PLAN_TASK_NOT_FOUND",
            )
        return row

    def _scope_anchor_for_plan(self, plan: MaintenancePreventivePlan) -> str:
        if plan.asset_id:
            return plan.asset_id
        if plan.component_id:
            component = self._component_repo.get(plan.component_id)
            if component is not None:
                return component.asset_id
        if plan.system_id:
            return plan.system_id
        return ""

    def _scope_anchor_for_task(self, row: MaintenancePreventivePlanTask) -> str:
        plan = self._preventive_plan_repo.get(row.plan_id)
        if plan is None:
            return ""
        return self._scope_anchor_for_plan(plan)

    def _require_scope_read(self, scope_id: str, *, operation_label: str) -> None:
        if scope_id:
            require_scope_permission(
                self._user_session,
                "maintenance",
                scope_id,
                "maintenance.read",
                operation_label=operation_label,
            )
            return
        if self._user_session is not None and self._user_session.is_scope_restricted("maintenance"):
            deny_maintenance_scope_access(
                self._user_session,
                operation_label=operation_label,
                message=(
                    f"Permission denied for {operation_label}. The record is "
                    "not anchored to a maintenance scope grant."
                ),
            )

    def _require_scope_manage(self, scope_id: str, *, operation_label: str) -> None:
        if scope_id:
            require_scope_permission(
                self._user_session,
                "maintenance",
                scope_id,
                "maintenance.manage",
                operation_label=operation_label,
            )
            return
        if self._user_session is not None and self._user_session.is_scope_restricted("maintenance"):
            deny_maintenance_scope_access(
                self._user_session,
                operation_label=operation_label,
                message=(
                    f"Permission denied for {operation_label}. The record is "
                    "not anchored to a maintenance scope grant."
                ),
            )

    def _record_change(self, action: str, row: MaintenancePreventivePlanTask) -> None:
        record_activity(
            self,
            action=action,
            entity_type="maintenance_preventive_plan_task",
            entity_id=row.id,
            module="maintenance",
            details={
                "organization_id": row.organization_id,
                "plan_id": row.plan_id,
                "task_template_id": row.task_template_id,
                "sequence_no": row.sequence_no,
                "trigger_scope": row.trigger_scope.value,
                "trigger_mode_override": row.trigger_mode_override.value if row.trigger_mode_override else None,
                "sensor_id_override": row.sensor_id_override,
                "is_mandatory": row.is_mandatory,
            },
        )
        domain_events.domain_changed.emit(
            DomainChangeEvent(
                category="module",
                scope_code="maintenance_management",
                entity_type="maintenance_preventive_plan_task",
                entity_id=row.id,
                source_event="maintenance_preventive_plan_tasks_changed",
            )
        )

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.read", operation_label=operation_label)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.manage", operation_label=operation_label)


__all__ = ["MaintenancePreventivePlanTaskService"]
