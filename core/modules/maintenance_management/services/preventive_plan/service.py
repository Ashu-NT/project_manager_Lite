from __future__ import annotations

from calendar import monthrange
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.modules.maintenance_management.domain import (
    MaintenanceAsset,
    MaintenanceAssetComponent,
    MaintenanceCalendarFrequencyUnit,
    MaintenancePreventivePlan,
    MaintenanceSensor,
    MaintenanceSystem,
    MaintenanceTriggerMode,
)
from core.modules.maintenance_management.interfaces import (
    MaintenanceAssetComponentRepository,
    MaintenanceAssetRepository,
    MaintenancePreventivePlanRepository,
    MaintenanceSensorRepository,
    MaintenanceSystemRepository,
)
from core.modules.maintenance_management.support import (
    coerce_calendar_frequency_unit,
    coerce_generation_lead_unit,
    coerce_optional_datetime,
    coerce_optional_decimal_value,
    coerce_optional_non_negative_int,
    coerce_plan_status,
    coerce_plan_type,
    coerce_priority,
    coerce_schedule_policy,
    coerce_sensor_direction,
    coerce_trigger_mode,
    normalize_maintenance_code,
    normalize_maintenance_name,
    normalize_optional_text,
)
from src.core.platform.access.authorization import filter_scope_rows, require_scope_permission
from core.platform.audit.helpers import record_audit
from src.core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.org.contracts import OrganizationRepository, SiteRepository
from src.core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from src.core.platform.org.domain import Organization, Site


class MaintenancePreventivePlanService:
    def __init__(
        self,
        session: Session,
        preventive_plan_repo: MaintenancePreventivePlanRepository,
        *,
        organization_repo: OrganizationRepository,
        site_repo: SiteRepository,
        asset_repo: MaintenanceAssetRepository,
        component_repo: MaintenanceAssetComponentRepository,
        system_repo: MaintenanceSystemRepository,
        sensor_repo: MaintenanceSensorRepository,
        user_session=None,
        audit_service=None,
    ) -> None:
        self._session = session
        self._preventive_plan_repo = preventive_plan_repo
        self._organization_repo = organization_repo
        self._site_repo = site_repo
        self._asset_repo = asset_repo
        self._component_repo = component_repo
        self._system_repo = system_repo
        self._sensor_repo = sensor_repo
        self._user_session = user_session
        self._audit_service = audit_service

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
        sensor_id: str | None = None,
    ) -> list[MaintenancePreventivePlan]:
        self._require_read("list maintenance preventive plans")
        organization = self._active_organization()
        if site_id is not None:
            self._get_site(site_id, organization=organization)
        if asset_id is not None:
            self._get_asset(asset_id, organization=organization)
        if component_id is not None:
            self._get_component(component_id, organization=organization)
        if system_id is not None:
            self._get_system(system_id, organization=organization)
        if sensor_id is not None:
            self._get_sensor(sensor_id, organization=organization)
        rows = self._preventive_plan_repo.list_for_organization(
            organization.id,
            active_only=active_only,
            site_id=site_id,
            asset_id=asset_id,
            component_id=component_id,
            system_id=system_id,
            status=coerce_plan_status(status) if status not in (None, "") else None,
            plan_type=coerce_plan_type(plan_type) if plan_type not in (None, "") else None,
            trigger_mode=coerce_trigger_mode(trigger_mode) if trigger_mode not in (None, "") else None,
            sensor_id=sensor_id,
        )
        return filter_scope_rows(
            rows,
            self._user_session,
            scope_type="maintenance",
            permission_code="maintenance.read",
            scope_id_getter=self._scope_anchor_for,
        )

    def search_preventive_plans(
        self,
        *,
        search_text: str = "",
        active_only: bool | None = None,
        site_id: str | None = None,
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        status: str | None = None,
        plan_type: str | None = None,
        trigger_mode: str | None = None,
    ) -> list[MaintenancePreventivePlan]:
        normalized_search = normalize_optional_text(search_text).lower()
        rows = self.list_preventive_plans(
            active_only=active_only,
            site_id=site_id,
            asset_id=asset_id,
            component_id=component_id,
            system_id=system_id,
            status=status,
            plan_type=plan_type,
            trigger_mode=trigger_mode,
        )
        if not normalized_search:
            return rows
        return [
            row
            for row in rows
            if normalized_search in " ".join(
                filter(
                    None,
                    [row.plan_code, row.name, row.description, row.plan_type.value, row.status.value, row.trigger_mode.value],
                )
            ).lower()
        ]

    def get_preventive_plan(self, preventive_plan_id: str) -> MaintenancePreventivePlan:
        self._require_read("view maintenance preventive plan")
        row = self._get_plan(preventive_plan_id, organization=self._active_organization())
        self._require_scope_read(self._scope_anchor_for(row), operation_label="view maintenance preventive plan")
        return row

    def find_preventive_plan_by_code(
        self,
        plan_code: str,
        *,
        active_only: bool | None = None,
    ) -> MaintenancePreventivePlan | None:
        self._require_read("resolve maintenance preventive plan")
        organization = self._active_organization()
        row = self._preventive_plan_repo.get_by_code(
            organization.id,
            normalize_maintenance_code(plan_code, label="Preventive plan code"),
        )
        if row is None:
            return None
        if active_only is not None and row.is_active != bool(active_only):
            return None
        visible_rows = filter_scope_rows(
            [row],
            self._user_session,
            scope_type="maintenance",
            permission_code="maintenance.read",
            scope_id_getter=self._scope_anchor_for,
        )
        return visible_rows[0] if visible_rows else None

    def create_preventive_plan(
        self,
        *,
        site_id: str,
        plan_code: str,
        name: str,
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        description: str = "",
        status=None,
        plan_type=None,
        priority=None,
        trigger_mode=None,
        schedule_policy=None,
        calendar_frequency_unit=None,
        calendar_frequency_value: int | str | None = None,
        generation_horizon_count: int | str | None = None,
        generation_lead_value: int | str | None = None,
        generation_lead_unit=None,
        sensor_id: str | None = None,
        sensor_threshold: Decimal | int | float | str | None = None,
        sensor_direction=None,
        sensor_reset_rule: str = "",
        last_generated_at=None,
        last_completed_at=None,
        next_due_at=None,
        next_due_counter: Decimal | int | float | str | None = None,
        requires_shutdown: bool = False,
        approval_required: bool = False,
        auto_generate_work_order: bool = False,
        is_active: bool = True,
        notes: str = "",
    ) -> MaintenancePreventivePlan:
        self._require_manage("create maintenance preventive plan")
        organization = self._active_organization()
        site = self._get_site(site_id, organization=organization)
        normalized_code = normalize_maintenance_code(plan_code, label="Preventive plan code")
        if self._preventive_plan_repo.get_by_code(organization.id, normalized_code) is not None:
            raise ValidationError(
                "Preventive plan code already exists in the active organization.",
                code="MAINTENANCE_PREVENTIVE_PLAN_CODE_EXISTS",
            )
        asset, component, system = self._resolve_context(
            organization=organization,
            site=site,
            asset_id=asset_id,
            component_id=component_id,
            system_id=system_id,
        )
        resolved_trigger_mode = coerce_trigger_mode(trigger_mode)
        resolved_schedule_policy = coerce_schedule_policy(schedule_policy)
        resolved_calendar_frequency_unit = coerce_calendar_frequency_unit(calendar_frequency_unit)
        resolved_calendar_frequency_value = coerce_optional_non_negative_int(
            calendar_frequency_value,
            label="Calendar frequency value",
        )
        resolved_generation_horizon_count = self._normalize_generation_horizon_count(generation_horizon_count)
        resolved_generation_lead_value = self._normalize_generation_lead_value(generation_lead_value)
        resolved_generation_lead_unit = coerce_generation_lead_unit(generation_lead_unit)
        resolved_sensor_threshold = coerce_optional_decimal_value(sensor_threshold, label="Sensor threshold")
        resolved_sensor_direction = coerce_sensor_direction(sensor_direction)
        sensor = self._resolve_sensor(
            organization=organization,
            site=site,
            asset=asset,
            component=component,
            system=system,
            sensor_id=normalize_optional_text(sensor_id) or None,
        )
        self._validate_trigger_configuration(
            trigger_mode=resolved_trigger_mode,
            calendar_frequency_unit=resolved_calendar_frequency_unit,
            calendar_frequency_value=resolved_calendar_frequency_value,
            sensor=sensor,
            sensor_threshold=resolved_sensor_threshold,
            sensor_direction=resolved_sensor_direction,
        )
        self._require_scope_manage(
            self._scope_anchor_from_context(asset=asset, component=component, system=system),
            operation_label="create maintenance preventive plan",
        )
        resolved_next_due_at = coerce_optional_datetime(next_due_at, label="Next due at")
        if resolved_next_due_at is None:
            resolved_next_due_at = self._derive_initial_next_due_at(
                trigger_mode=resolved_trigger_mode,
                calendar_frequency_unit=resolved_calendar_frequency_unit,
                calendar_frequency_value=resolved_calendar_frequency_value,
            )
        row = MaintenancePreventivePlan.create(
            organization_id=organization.id,
            site_id=site.id,
            plan_code=normalized_code,
            name=normalize_maintenance_name(name, label="Preventive plan name"),
            asset_id=asset.id if asset is not None else None,
            component_id=component.id if component is not None else None,
            system_id=system.id if system is not None else None,
            description=normalize_optional_text(description),
            status=coerce_plan_status(status),
            plan_type=coerce_plan_type(plan_type),
            priority=coerce_priority(priority),
            trigger_mode=resolved_trigger_mode,
            schedule_policy=resolved_schedule_policy,
            calendar_frequency_unit=resolved_calendar_frequency_unit,
            calendar_frequency_value=resolved_calendar_frequency_value,
            generation_horizon_count=resolved_generation_horizon_count,
            generation_lead_value=resolved_generation_lead_value,
            generation_lead_unit=resolved_generation_lead_unit,
            sensor_id=sensor.id if sensor is not None else None,
            sensor_threshold=resolved_sensor_threshold,
            sensor_direction=resolved_sensor_direction,
            sensor_reset_rule=normalize_optional_text(sensor_reset_rule),
            last_generated_at=coerce_optional_datetime(last_generated_at, label="Last generated at"),
            last_completed_at=coerce_optional_datetime(last_completed_at, label="Last completed at"),
            next_due_at=resolved_next_due_at,
            next_due_counter=coerce_optional_decimal_value(next_due_counter, label="Next due counter"),
            requires_shutdown=bool(requires_shutdown),
            approval_required=bool(approval_required),
            auto_generate_work_order=bool(auto_generate_work_order),
            is_active=bool(is_active),
            notes=normalize_optional_text(notes),
        )
        try:
            self._preventive_plan_repo.add(row)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Preventive plan code already exists in the active organization.",
                code="MAINTENANCE_PREVENTIVE_PLAN_CODE_EXISTS",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_preventive_plan.create", row)
        return row

    def update_preventive_plan(
        self,
        preventive_plan_id: str,
        *,
        site_id: str | None = None,
        plan_code: str | None = None,
        name: str | None = None,
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        description: str | None = None,
        status=None,
        plan_type=None,
        priority=None,
        trigger_mode=None,
        schedule_policy=None,
        calendar_frequency_unit=None,
        calendar_frequency_value: int | str | None = None,
        generation_horizon_count: int | str | None = None,
        generation_lead_value: int | str | None = None,
        generation_lead_unit=None,
        sensor_id: str | None = None,
        sensor_threshold: Decimal | int | float | str | None = None,
        sensor_direction=None,
        sensor_reset_rule: str | None = None,
        last_generated_at=None,
        last_completed_at=None,
        next_due_at=None,
        next_due_counter: Decimal | int | float | str | None = None,
        requires_shutdown: bool | None = None,
        approval_required: bool | None = None,
        auto_generate_work_order: bool | None = None,
        is_active: bool | None = None,
        notes: str | None = None,
        expected_version: int | None = None,
    ) -> MaintenancePreventivePlan:
        self._require_manage("update maintenance preventive plan")
        organization = self._active_organization()
        row = self.get_preventive_plan(preventive_plan_id)
        if expected_version is not None and row.version != expected_version:
            raise ConcurrencyError(
                "Maintenance preventive plan changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        target_site = (
            self._get_site(site_id, organization=organization)
            if site_id is not None
            else self._get_site(row.site_id, organization=organization)
        )
        asset, component, system = self._resolve_context(
            organization=organization,
            site=target_site,
            asset_id=row.asset_id if asset_id is None else (normalize_optional_text(asset_id) or None),
            component_id=row.component_id if component_id is None else (normalize_optional_text(component_id) or None),
            system_id=row.system_id if system_id is None else (normalize_optional_text(system_id) or None),
        )
        resolved_trigger_mode = row.trigger_mode if trigger_mode is None else coerce_trigger_mode(trigger_mode)
        resolved_schedule_policy = (
            row.schedule_policy if schedule_policy is None else coerce_schedule_policy(schedule_policy)
        )
        resolved_calendar_frequency_unit = (
            row.calendar_frequency_unit
            if calendar_frequency_unit is None
            else coerce_calendar_frequency_unit(calendar_frequency_unit)
        )
        resolved_calendar_frequency_value = (
            row.calendar_frequency_value
            if calendar_frequency_value is None
            else coerce_optional_non_negative_int(calendar_frequency_value, label="Calendar frequency value")
        )
        resolved_generation_horizon_count = (
            row.generation_horizon_count
            if generation_horizon_count is None
            else self._normalize_generation_horizon_count(generation_horizon_count)
        )
        resolved_generation_lead_value = (
            row.generation_lead_value
            if generation_lead_value is None
            else self._normalize_generation_lead_value(generation_lead_value)
        )
        resolved_generation_lead_unit = (
            row.generation_lead_unit if generation_lead_unit is None else coerce_generation_lead_unit(generation_lead_unit)
        )
        resolved_sensor_threshold = (
            row.sensor_threshold
            if sensor_threshold is None
            else coerce_optional_decimal_value(sensor_threshold, label="Sensor threshold")
        )
        resolved_sensor_direction = (
            row.sensor_direction if sensor_direction is None else coerce_sensor_direction(sensor_direction)
        )
        sensor = self._resolve_sensor(
            organization=organization,
            site=target_site,
            asset=asset,
            component=component,
            system=system,
            sensor_id=row.sensor_id if sensor_id is None else (normalize_optional_text(sensor_id) or None),
        )
        self._validate_trigger_configuration(
            trigger_mode=resolved_trigger_mode,
            calendar_frequency_unit=resolved_calendar_frequency_unit,
            calendar_frequency_value=resolved_calendar_frequency_value,
            sensor=sensor,
            sensor_threshold=resolved_sensor_threshold,
            sensor_direction=resolved_sensor_direction,
        )
        self._require_scope_manage(
            self._scope_anchor_from_context(asset=asset, component=component, system=system),
            operation_label="update maintenance preventive plan",
        )
        if plan_code is not None:
            normalized_code = normalize_maintenance_code(plan_code, label="Preventive plan code")
            existing = self._preventive_plan_repo.get_by_code(organization.id, normalized_code)
            if existing is not None and existing.id != row.id:
                raise ValidationError(
                    "Preventive plan code already exists in the active organization.",
                    code="MAINTENANCE_PREVENTIVE_PLAN_CODE_EXISTS",
                )
            row.plan_code = normalized_code
        if name is not None:
            row.name = normalize_maintenance_name(name, label="Preventive plan name")
        if description is not None:
            row.description = normalize_optional_text(description)
        if status is not None:
            row.status = coerce_plan_status(status)
        if plan_type is not None:
            row.plan_type = coerce_plan_type(plan_type)
        if priority is not None:
            row.priority = coerce_priority(priority)
        row.site_id = target_site.id
        row.asset_id = asset.id if asset is not None else None
        row.component_id = component.id if component is not None else None
        row.system_id = system.id if system is not None else None
        row.trigger_mode = resolved_trigger_mode
        row.schedule_policy = resolved_schedule_policy
        row.calendar_frequency_unit = resolved_calendar_frequency_unit
        row.calendar_frequency_value = resolved_calendar_frequency_value
        row.generation_horizon_count = resolved_generation_horizon_count
        row.generation_lead_value = resolved_generation_lead_value
        row.generation_lead_unit = resolved_generation_lead_unit
        row.sensor_id = sensor.id if sensor is not None else None
        row.sensor_threshold = resolved_sensor_threshold
        row.sensor_direction = resolved_sensor_direction
        if sensor_reset_rule is not None:
            row.sensor_reset_rule = normalize_optional_text(sensor_reset_rule)
        if last_generated_at is not None:
            row.last_generated_at = coerce_optional_datetime(last_generated_at, label="Last generated at")
        if last_completed_at is not None:
            row.last_completed_at = coerce_optional_datetime(last_completed_at, label="Last completed at")
        if next_due_at is not None:
            row.next_due_at = coerce_optional_datetime(next_due_at, label="Next due at")
        elif (
            row.next_due_at is None
            and row.trigger_mode in (MaintenanceTriggerMode.CALENDAR, MaintenanceTriggerMode.HYBRID)
            and row.calendar_frequency_unit is not None
            and row.calendar_frequency_value not in (None, 0)
        ):
            row.next_due_at = self._derive_initial_next_due_at(
                trigger_mode=row.trigger_mode,
                calendar_frequency_unit=row.calendar_frequency_unit,
                calendar_frequency_value=row.calendar_frequency_value,
            )
        if next_due_counter is not None:
            row.next_due_counter = coerce_optional_decimal_value(next_due_counter, label="Next due counter")
        if requires_shutdown is not None:
            row.requires_shutdown = bool(requires_shutdown)
        if approval_required is not None:
            row.approval_required = bool(approval_required)
        if auto_generate_work_order is not None:
            row.auto_generate_work_order = bool(auto_generate_work_order)
        if is_active is not None:
            row.is_active = bool(is_active)
        if notes is not None:
            row.notes = normalize_optional_text(notes)
        row.updated_at = datetime.now(timezone.utc)
        try:
            self._preventive_plan_repo.update(row)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Preventive plan code already exists in the active organization.",
                code="MAINTENANCE_PREVENTIVE_PLAN_CODE_EXISTS",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_preventive_plan.update", row)
        return row

    def _resolve_context(
        self,
        *,
        organization: Organization,
        site: Site,
        asset_id: str | None,
        component_id: str | None,
        system_id: str | None,
    ) -> tuple[MaintenanceAsset | None, MaintenanceAssetComponent | None, MaintenanceSystem | None]:
        asset = self._get_asset(asset_id, organization=organization) if asset_id else None
        component = self._get_component(component_id, organization=organization) if component_id else None
        system = self._get_system(system_id, organization=organization) if system_id else None
        if component is not None:
            component_asset = self._get_asset(component.asset_id, organization=organization)
            if asset is None:
                asset = component_asset
            elif asset.id != component_asset.id:
                raise ValidationError(
                    "Selected component must belong to the selected asset.",
                    code="MAINTENANCE_PREVENTIVE_PLAN_COMPONENT_ASSET_MISMATCH",
                )
        if asset is None and component is None and system is None:
            raise ValidationError(
                "Preventive plan must be linked to an asset, component, or system.",
                code="MAINTENANCE_PREVENTIVE_PLAN_CONTEXT_REQUIRED",
            )
        if asset is not None and asset.site_id != site.id:
            raise ValidationError(
                "Selected asset must belong to the selected site.",
                code="MAINTENANCE_PREVENTIVE_PLAN_SITE_MISMATCH",
            )
        if system is not None and system.site_id != site.id:
            raise ValidationError(
                "Selected system must belong to the selected site.",
                code="MAINTENANCE_PREVENTIVE_PLAN_SITE_MISMATCH",
            )
        if asset is not None and system is not None and asset.system_id and asset.system_id != system.id:
            raise ValidationError(
                "Selected asset is already anchored to a different maintenance system.",
                code="MAINTENANCE_PREVENTIVE_PLAN_SYSTEM_MISMATCH",
            )
        return asset, component, system

    def _resolve_sensor(
        self,
        *,
        organization: Organization,
        site: Site,
        asset: MaintenanceAsset | None,
        component: MaintenanceAssetComponent | None,
        system: MaintenanceSystem | None,
        sensor_id: str | None,
    ) -> MaintenanceSensor | None:
        if not sensor_id:
            return None
        sensor = self._get_sensor(sensor_id, organization=organization)
        if sensor.site_id != site.id:
            raise ValidationError(
                "Selected sensor must belong to the selected site.",
                code="MAINTENANCE_PREVENTIVE_PLAN_SENSOR_SITE_MISMATCH",
            )
        if asset is not None and sensor.asset_id not in (None, asset.id):
            raise ValidationError(
                "Selected sensor must align with the selected asset context.",
                code="MAINTENANCE_PREVENTIVE_PLAN_SENSOR_CONTEXT_MISMATCH",
            )
        if component is not None and sensor.component_id not in (None, component.id):
            raise ValidationError(
                "Selected sensor must align with the selected component context.",
                code="MAINTENANCE_PREVENTIVE_PLAN_SENSOR_CONTEXT_MISMATCH",
            )
        if system is not None and sensor.system_id not in (None, system.id):
            raise ValidationError(
                "Selected sensor must align with the selected system context.",
                code="MAINTENANCE_PREVENTIVE_PLAN_SENSOR_CONTEXT_MISMATCH",
            )
        return sensor

    def _validate_trigger_configuration(
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
                    "Calendar-triggered preventive plans require frequency unit and value.",
                    code="MAINTENANCE_PREVENTIVE_PLAN_CALENDAR_REQUIRED",
                )
            if sensor is not None or sensor_threshold is not None or sensor_direction is not None:
                raise ValidationError(
                    "Calendar-triggered preventive plans cannot define sensor trigger fields.",
                    code="MAINTENANCE_PREVENTIVE_PLAN_SENSOR_NOT_ALLOWED",
                )
            return
        if trigger_mode == MaintenanceTriggerMode.SENSOR:
            if not has_sensor:
                raise ValidationError(
                    "Sensor-triggered preventive plans require sensor, threshold, and direction.",
                    code="MAINTENANCE_PREVENTIVE_PLAN_SENSOR_REQUIRED",
                )
            if calendar_frequency_unit is not None or calendar_frequency_value is not None:
                raise ValidationError(
                    "Sensor-triggered preventive plans cannot define calendar trigger fields.",
                    code="MAINTENANCE_PREVENTIVE_PLAN_CALENDAR_NOT_ALLOWED",
                )
            return
        if not has_calendar:
            raise ValidationError(
                "Hybrid preventive plans require calendar frequency unit and value.",
                code="MAINTENANCE_PREVENTIVE_PLAN_CALENDAR_REQUIRED",
            )
        if not has_sensor:
            raise ValidationError(
                "Hybrid preventive plans require sensor, threshold, and direction.",
                code="MAINTENANCE_PREVENTIVE_PLAN_SENSOR_REQUIRED",
            )

    def _normalize_generation_horizon_count(self, value: int | str | None) -> int:
        resolved = coerce_optional_non_negative_int(value, label="Generation horizon count")
        if resolved in (None, 0):
            return 13
        return resolved

    def _normalize_generation_lead_value(self, value: int | str | None) -> int:
        resolved = coerce_optional_non_negative_int(value, label="Generation lead value")
        if resolved is None:
            return 0
        return resolved

    def _derive_initial_next_due_at(
        self,
        *,
        trigger_mode: MaintenanceTriggerMode,
        calendar_frequency_unit: MaintenanceCalendarFrequencyUnit | None,
        calendar_frequency_value: int | None,
    ) -> datetime | None:
        if trigger_mode not in (MaintenanceTriggerMode.CALENDAR, MaintenanceTriggerMode.HYBRID):
            return None
        if calendar_frequency_unit is None or calendar_frequency_value in (None, 0):
            return None
        return self._advance_calendar_due(
            datetime.now(timezone.utc),
            calendar_frequency_unit,
            calendar_frequency_value,
        )

    def _advance_calendar_due(
        self,
        anchor: datetime,
        unit: MaintenanceCalendarFrequencyUnit,
        value: int,
    ) -> datetime:
        if unit == MaintenanceCalendarFrequencyUnit.DAILY:
            return anchor + timedelta(days=value)
        if unit == MaintenanceCalendarFrequencyUnit.WEEKLY:
            return anchor + timedelta(weeks=value)
        if unit == MaintenanceCalendarFrequencyUnit.CUSTOM_DAYS:
            return anchor + timedelta(days=value)
        months = value
        if unit == MaintenanceCalendarFrequencyUnit.QUARTERLY:
            months = value * 3
        elif unit == MaintenanceCalendarFrequencyUnit.YEARLY:
            months = value * 12
        total_month = anchor.month - 1 + months
        year = anchor.year + total_month // 12
        month = total_month % 12 + 1
        day = min(anchor.day, monthrange(year, month)[1])
        return anchor.replace(year=year, month=month, day=day)

    def _scope_anchor_from_context(
        self,
        *,
        asset: MaintenanceAsset | None,
        component: MaintenanceAssetComponent | None,
        system: MaintenanceSystem | None,
    ) -> str:
        if asset is not None:
            return asset.id
        if component is not None:
            return component.asset_id
        if system is not None:
            return system.id
        return ""

    def _scope_anchor_for(self, row: MaintenancePreventivePlan) -> str:
        if row.asset_id:
            return row.asset_id
        if row.component_id:
            component = self._component_repo.get(row.component_id)
            if component is not None:
                return component.asset_id
        if row.system_id:
            return row.system_id
        return ""

    def _active_organization(self) -> Organization:
        organization = self._organization_repo.get_active()
        if organization is None:
            raise NotFoundError("Active organization not found.", code="ORGANIZATION_NOT_FOUND")
        return organization

    def _get_plan(self, preventive_plan_id: str, *, organization: Organization) -> MaintenancePreventivePlan:
        row = self._preventive_plan_repo.get(preventive_plan_id)
        if row is None or row.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance preventive plan not found in the active organization.",
                code="MAINTENANCE_PREVENTIVE_PLAN_NOT_FOUND",
            )
        return row

    def _get_site(self, site_id: str, *, organization: Organization) -> Site:
        row = self._site_repo.get(site_id)
        if row is None or row.organization_id != organization.id:
            raise NotFoundError("Site not found in the active organization.", code="SITE_NOT_FOUND")
        return row

    def _get_asset(self, asset_id: str, *, organization: Organization) -> MaintenanceAsset:
        row = self._asset_repo.get(asset_id)
        if row is None or row.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance asset not found in the active organization.",
                code="MAINTENANCE_ASSET_NOT_FOUND",
            )
        return row

    def _get_component(self, component_id: str, *, organization: Organization) -> MaintenanceAssetComponent:
        row = self._component_repo.get(component_id)
        if row is None or row.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance asset component not found in the active organization.",
                code="MAINTENANCE_COMPONENT_NOT_FOUND",
            )
        return row

    def _get_system(self, system_id: str, *, organization: Organization) -> MaintenanceSystem:
        row = self._system_repo.get(system_id)
        if row is None or row.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance system not found in the active organization.",
                code="MAINTENANCE_SYSTEM_NOT_FOUND",
            )
        return row

    def _get_sensor(self, sensor_id: str, *, organization: Organization) -> MaintenanceSensor:
        row = self._sensor_repo.get(sensor_id)
        if row is None or row.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance sensor not found in the active organization.",
                code="MAINTENANCE_SENSOR_NOT_FOUND",
            )
        return row

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
            raise BusinessRuleError(
                f"Permission denied for {operation_label}. The record is not anchored to a maintenance scope grant.",
                code="PERMISSION_DENIED",
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
            raise BusinessRuleError(
                f"Permission denied for {operation_label}. The record is not anchored to a maintenance scope grant.",
                code="PERMISSION_DENIED",
            )

    def _record_change(self, action: str, row: MaintenancePreventivePlan) -> None:
        record_audit(
            self,
            action=action,
            entity_type="maintenance_preventive_plan",
            entity_id=row.id,
            details={
                "organization_id": row.organization_id,
                "site_id": row.site_id,
                "plan_code": row.plan_code,
                "name": row.name,
                "asset_id": row.asset_id,
                "component_id": row.component_id,
                "system_id": row.system_id,
                "status": row.status.value,
                "plan_type": row.plan_type.value,
                "trigger_mode": row.trigger_mode.value,
                "sensor_id": row.sensor_id,
                "auto_generate_work_order": row.auto_generate_work_order,
                "is_active": row.is_active,
            },
        )
        domain_events.domain_changed.emit(
            DomainChangeEvent(
                category="module",
                scope_code="maintenance_management",
                entity_type="maintenance_preventive_plan",
                entity_id=row.id,
                source_event="maintenance_preventive_plans_changed",
            )
        )

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.read", operation_label=operation_label)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.manage", operation_label=operation_label)


__all__ = ["MaintenancePreventivePlanService"]
