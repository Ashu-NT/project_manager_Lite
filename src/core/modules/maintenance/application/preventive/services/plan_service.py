"""Preventive plan CRUD service — create, update, query preventive plans."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.maintenance.domain import (
    MaintenanceAsset,
    MaintenanceAssetComponent,
    MaintenancePreventivePlan,
    MaintenanceSensor,
    MaintenanceSystem,
    MaintenanceTriggerMode,
)
from src.core.modules.maintenance.contracts.repositories import (
    MaintenanceAssetComponentRepository,
    MaintenanceAssetRepository,
    MaintenancePreventivePlanRepository,
    MaintenanceSensorRepository,
    MaintenanceSystemRepository,
)
from src.core.modules.maintenance.application.common.support import (
    coerce_plan_status,
    coerce_plan_type,
    coerce_trigger_mode,
    normalize_maintenance_code,
    normalize_optional_text,
)
from src.core.modules.maintenance.application.common.scope_authorization import (
    deny_maintenance_scope_access,
)
from src.core.modules.maintenance.application.preventive.utils.date_utils import advance_calendar_due
from src.core.platform.access.authorization import filter_scope_rows, require_scope_permission
from src.core.shared.activity.activity_recorder import record_activity
from src.core.platform.auth.authorization import require_permission
from src.core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.contract.master_data.org.contracts import OrganizationRepository
from src.core.platform.contract.master_data.site.contracts import SiteRepository
from src.core.platform.tenancy.tenant_context import (
    TenantContextService,
    require_tenant_context_service,
)
from src.core.shared.events.domain_events import DomainChangeEvent, domain_events
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.domain.master_data.site import Site


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
        tenant_context_service: TenantContextService | None = None,
        user_session=None,
        activity_service=None,
    ) -> None:
        self._session = session
        self._preventive_plan_repo = preventive_plan_repo
        self._organization_repo = organization_repo
        self._tenant_context_service = require_tenant_context_service(
            tenant_context_service,
            consumer_label="MaintenancePreventivePlanService",
        )
        self._site_repo = site_repo
        self._asset_repo = asset_repo
        self._component_repo = component_repo
        self._system_repo = system_repo
        self._sensor_repo = sensor_repo
        self._user_session = user_session
        self._activity_service = activity_service

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
            rows, self._user_session,
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
            active_only=active_only, site_id=site_id, asset_id=asset_id,
            component_id=component_id, system_id=system_id,
            status=status, plan_type=plan_type, trigger_mode=trigger_mode,
        )
        if not normalized_search:
            return rows
        return [
            row for row in rows
            if normalized_search in " ".join(filter(None, [
                row.plan_code, row.name, row.description,
                row.plan_type.value, row.status.value, row.trigger_mode.value,
            ])).lower()
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
        visible = filter_scope_rows(
            [row], self._user_session,
            scope_type="maintenance", permission_code="maintenance.read",
            scope_id_getter=self._scope_anchor_for,
        )
        return visible[0] if visible else None

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
        asset, component, system = self._resolve_context(
            organization=organization, site=site,
            asset_id=asset_id, component_id=component_id, system_id=system_id,
        )
        sensor = self._resolve_sensor(
            organization=organization, site=site, asset=asset, component=component, system=system,
            sensor_id=normalize_optional_text(sensor_id) or None,
        )
        row = MaintenancePreventivePlan.create(
            organization_id=organization.id,
            site_id=site.id,
            plan_code=plan_code,
            name=name,
            asset_id=asset.id if asset is not None else None,
            component_id=component.id if component is not None else None,
            system_id=system.id if system is not None else None,
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
            sensor_id=sensor.id if sensor is not None else None,
            sensor_threshold=sensor_threshold,
            sensor_direction=sensor_direction,
            sensor_reset_rule=sensor_reset_rule,
            last_generated_at=last_generated_at,
            last_completed_at=last_completed_at,
            next_due_at=next_due_at,
            next_due_counter=next_due_counter,
            requires_shutdown=bool(requires_shutdown),
            approval_required=bool(approval_required),
            auto_generate_work_order=bool(auto_generate_work_order),
            is_active=bool(is_active),
            notes=notes,
        )
        if self._preventive_plan_repo.get_by_code(organization.id, row.plan_code) is not None:
            raise ValidationError(
                "Preventive plan code already exists in the active organization.",
                code="MAINTENANCE_PREVENTIVE_PLAN_CODE_EXISTS",
            )
        self._validate_trigger_configuration(
            trigger_mode=row.trigger_mode,
            calendar_frequency_unit=row.calendar_frequency_unit,
            calendar_frequency_value=row.calendar_frequency_value,
            sensor=sensor,
            sensor_threshold=row.sensor_threshold,
            sensor_direction=row.sensor_direction,
        )
        self._require_scope_manage(
            self._scope_anchor_from_context(asset=asset, component=component, system=system),
            operation_label="create maintenance preventive plan",
        )
        if row.next_due_at is None:
            derived_next_due_at = self._derive_initial_next_due_at(
                trigger_mode=row.trigger_mode,
                calendar_frequency_unit=row.calendar_frequency_unit,
                calendar_frequency_value=row.calendar_frequency_value,
            )
            if derived_next_due_at is not None:
                row = replace(row, next_due_at=derived_next_due_at)
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
            organization=organization, site=target_site,
            asset_id=row.asset_id if asset_id is None else (normalize_optional_text(asset_id) or None),
            component_id=row.component_id if component_id is None else (normalize_optional_text(component_id) or None),
            system_id=row.system_id if system_id is None else (normalize_optional_text(system_id) or None),
        )
        sensor = self._resolve_sensor(
            organization=organization, site=target_site, asset=asset, component=component, system=system,
            sensor_id=row.sensor_id if sensor_id is None else (normalize_optional_text(sensor_id) or None),
        )
        updated = replace(
            row,
            site_id=target_site.id,
            plan_code=row.plan_code if plan_code is None else plan_code,
            name=row.name if name is None else name,
            asset_id=asset.id if asset is not None else None,
            component_id=component.id if component is not None else None,
            system_id=system.id if system is not None else None,
            description=row.description if description is None else description,
            status=row.status if status is None else status,
            plan_type=row.plan_type if plan_type is None else plan_type,
            priority=row.priority if priority is None else priority,
            trigger_mode=row.trigger_mode if trigger_mode is None else trigger_mode,
            schedule_policy=row.schedule_policy if schedule_policy is None else schedule_policy,
            calendar_frequency_unit=(
                row.calendar_frequency_unit
                if calendar_frequency_unit is None
                else calendar_frequency_unit
            ),
            calendar_frequency_value=(
                row.calendar_frequency_value
                if calendar_frequency_value is None
                else calendar_frequency_value
            ),
            generation_horizon_count=(
                row.generation_horizon_count
                if generation_horizon_count is None
                else generation_horizon_count
            ),
            generation_lead_value=(
                row.generation_lead_value
                if generation_lead_value is None
                else generation_lead_value
            ),
            generation_lead_unit=(
                row.generation_lead_unit
                if generation_lead_unit is None
                else generation_lead_unit
            ),
            sensor_id=sensor.id if sensor is not None else None,
            sensor_threshold=row.sensor_threshold if sensor_threshold is None else sensor_threshold,
            sensor_direction=row.sensor_direction if sensor_direction is None else sensor_direction,
            sensor_reset_rule=row.sensor_reset_rule if sensor_reset_rule is None else sensor_reset_rule,
            last_generated_at=(
                row.last_generated_at if last_generated_at is None else last_generated_at
            ),
            last_completed_at=(
                row.last_completed_at if last_completed_at is None else last_completed_at
            ),
            next_due_at=row.next_due_at if next_due_at is None else next_due_at,
            next_due_counter=(
                row.next_due_counter if next_due_counter is None else next_due_counter
            ),
            requires_shutdown=(
                row.requires_shutdown if requires_shutdown is None else bool(requires_shutdown)
            ),
            approval_required=(
                row.approval_required if approval_required is None else bool(approval_required)
            ),
            auto_generate_work_order=(
                row.auto_generate_work_order
                if auto_generate_work_order is None
                else bool(auto_generate_work_order)
            ),
            is_active=row.is_active if is_active is None else bool(is_active),
            notes=row.notes if notes is None else notes,
            updated_at=datetime.now(timezone.utc),
        )
        self._validate_trigger_configuration(
            trigger_mode=updated.trigger_mode,
            calendar_frequency_unit=updated.calendar_frequency_unit,
            calendar_frequency_value=updated.calendar_frequency_value,
            sensor=sensor,
            sensor_threshold=updated.sensor_threshold,
            sensor_direction=updated.sensor_direction,
        )
        self._require_scope_manage(
            self._scope_anchor_from_context(asset=asset, component=component, system=system),
            operation_label="update maintenance preventive plan",
        )
        existing = self._preventive_plan_repo.get_by_code(organization.id, updated.plan_code)
        if existing is not None and existing.id != row.id:
            raise ValidationError(
                "Preventive plan code already exists in the active organization.",
                code="MAINTENANCE_PREVENTIVE_PLAN_CODE_EXISTS",
            )
        if (
            next_due_at is None
            and updated.next_due_at is None
            and updated.trigger_mode in (MaintenanceTriggerMode.CALENDAR, MaintenanceTriggerMode.HYBRID)
            and updated.calendar_frequency_unit is not None
            and updated.calendar_frequency_value not in (None, 0)
        ):
            updated = replace(
                updated,
                next_due_at=self._derive_initial_next_due_at(
                    trigger_mode=updated.trigger_mode,
                    calendar_frequency_unit=updated.calendar_frequency_unit,
                    calendar_frequency_value=updated.calendar_frequency_value,
                ),
            )
        try:
            self._preventive_plan_repo.update(updated)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Preventive plan code already exists in the active organization.", code="MAINTENANCE_PREVENTIVE_PLAN_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_preventive_plan.update", updated)
        return updated

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_context(
        self, *, organization, site, asset_id, component_id, system_id
    ) -> tuple[MaintenanceAsset | None, MaintenanceAssetComponent | None, MaintenanceSystem | None]:
        asset = self._get_asset(asset_id, organization=organization) if asset_id else None
        component = self._get_component(component_id, organization=organization) if component_id else None
        system = self._get_system(system_id, organization=organization) if system_id else None
        if component is not None:
            component_asset = self._get_asset(component.asset_id, organization=organization)
            if asset is None:
                asset = component_asset
            elif asset.id != component_asset.id:
                raise ValidationError("Selected component must belong to the selected asset.", code="MAINTENANCE_PREVENTIVE_PLAN_COMPONENT_ASSET_MISMATCH")
        if asset is None and component is None and system is None:
            raise ValidationError("Preventive plan must be linked to an asset, component, or system.", code="MAINTENANCE_PREVENTIVE_PLAN_CONTEXT_REQUIRED")
        if asset is not None and asset.site_id != site.id:
            raise ValidationError("Selected asset must belong to the selected site.", code="MAINTENANCE_PREVENTIVE_PLAN_SITE_MISMATCH")
        if system is not None and system.site_id != site.id:
            raise ValidationError("Selected system must belong to the selected site.", code="MAINTENANCE_PREVENTIVE_PLAN_SITE_MISMATCH")
        if asset is not None and system is not None and asset.system_id and asset.system_id != system.id:
            raise ValidationError("Selected asset is already anchored to a different maintenance system.", code="MAINTENANCE_PREVENTIVE_PLAN_SYSTEM_MISMATCH")
        return asset, component, system

    def _resolve_sensor(self, *, organization, site, asset, component, system, sensor_id) -> MaintenanceSensor | None:
        if not sensor_id:
            return None
        sensor = self._get_sensor(sensor_id, organization=organization)
        if sensor.site_id != site.id:
            raise ValidationError("Selected sensor must belong to the selected site.", code="MAINTENANCE_PREVENTIVE_PLAN_SENSOR_SITE_MISMATCH")
        if asset is not None and sensor.asset_id not in (None, asset.id):
            raise ValidationError("Selected sensor must align with the selected asset context.", code="MAINTENANCE_PREVENTIVE_PLAN_SENSOR_CONTEXT_MISMATCH")
        if component is not None and sensor.component_id not in (None, component.id):
            raise ValidationError("Selected sensor must align with the selected component context.", code="MAINTENANCE_PREVENTIVE_PLAN_SENSOR_CONTEXT_MISMATCH")
        if system is not None and sensor.system_id not in (None, system.id):
            raise ValidationError("Selected sensor must align with the selected system context.", code="MAINTENANCE_PREVENTIVE_PLAN_SENSOR_CONTEXT_MISMATCH")
        return sensor

    def _validate_trigger_configuration(self, *, trigger_mode, calendar_frequency_unit, calendar_frequency_value, sensor, sensor_threshold, sensor_direction) -> None:
        has_calendar = calendar_frequency_unit is not None and calendar_frequency_value not in (None, 0)
        has_sensor = sensor is not None and sensor_threshold is not None and sensor_direction is not None
        if trigger_mode == MaintenanceTriggerMode.CALENDAR:
            if not has_calendar:
                raise ValidationError("Calendar-triggered preventive plans require frequency unit and value.", code="MAINTENANCE_PREVENTIVE_PLAN_CALENDAR_REQUIRED")
            if sensor is not None or sensor_threshold is not None or sensor_direction is not None:
                raise ValidationError("Calendar-triggered preventive plans cannot define sensor trigger fields.", code="MAINTENANCE_PREVENTIVE_PLAN_SENSOR_NOT_ALLOWED")
            return
        if trigger_mode == MaintenanceTriggerMode.SENSOR:
            if not has_sensor:
                raise ValidationError("Sensor-triggered preventive plans require sensor, threshold, and direction.", code="MAINTENANCE_PREVENTIVE_PLAN_SENSOR_REQUIRED")
            if calendar_frequency_unit is not None or calendar_frequency_value is not None:
                raise ValidationError("Sensor-triggered preventive plans cannot define calendar trigger fields.", code="MAINTENANCE_PREVENTIVE_PLAN_CALENDAR_NOT_ALLOWED")
            return
        if not has_calendar:
            raise ValidationError("Hybrid preventive plans require calendar frequency unit and value.", code="MAINTENANCE_PREVENTIVE_PLAN_CALENDAR_REQUIRED")
        if not has_sensor:
            raise ValidationError("Hybrid preventive plans require sensor, threshold, and direction.", code="MAINTENANCE_PREVENTIVE_PLAN_SENSOR_REQUIRED")

    def _derive_initial_next_due_at(self, *, trigger_mode, calendar_frequency_unit, calendar_frequency_value) -> datetime | None:
        if trigger_mode not in (MaintenanceTriggerMode.CALENDAR, MaintenanceTriggerMode.HYBRID):
            return None
        if calendar_frequency_unit is None or calendar_frequency_value in (None, 0):
            return None
        return advance_calendar_due(datetime.now(timezone.utc), calendar_frequency_unit, calendar_frequency_value)

    def _scope_anchor_from_context(self, *, asset, component, system) -> str:
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
        return self._tenant_context_service.require_context(
            operation_label="maintenance preventive plans"
        ).organization

    def _get_plan(self, preventive_plan_id: str, *, organization: Organization) -> MaintenancePreventivePlan:
        row = self._preventive_plan_repo.get(preventive_plan_id)
        if row is None or row.organization_id != organization.id:
            raise NotFoundError("Maintenance preventive plan not found in the active organization.", code="MAINTENANCE_PREVENTIVE_PLAN_NOT_FOUND")
        return row

    def _get_site(self, site_id: str, *, organization: Organization) -> Site:
        row = self._site_repo.get(site_id)
        if row is None or row.organization_id != organization.id:
            raise NotFoundError("Site not found in the active organization.", code="SITE_NOT_FOUND")
        return row

    def _get_asset(self, asset_id: str, *, organization: Organization):
        row = self._asset_repo.get(asset_id)
        if row is None or row.organization_id != organization.id:
            raise NotFoundError("Maintenance asset not found in the active organization.", code="MAINTENANCE_ASSET_NOT_FOUND")
        return row

    def _get_component(self, component_id: str, *, organization: Organization):
        row = self._component_repo.get(component_id)
        if row is None or row.organization_id != organization.id:
            raise NotFoundError("Maintenance asset component not found in the active organization.", code="MAINTENANCE_COMPONENT_NOT_FOUND")
        return row

    def _get_system(self, system_id: str, *, organization: Organization):
        row = self._system_repo.get(system_id)
        if row is None or row.organization_id != organization.id:
            raise NotFoundError("Maintenance system not found in the active organization.", code="MAINTENANCE_SYSTEM_NOT_FOUND")
        return row

    def _get_sensor(self, sensor_id: str, *, organization: Organization):
        row = self._sensor_repo.get(sensor_id)
        if row is None or row.organization_id != organization.id:
            raise NotFoundError("Maintenance sensor not found in the active organization.", code="MAINTENANCE_SENSOR_NOT_FOUND")
        return row

    def _require_scope_read(self, scope_id: str, *, operation_label: str) -> None:
        if scope_id:
            require_scope_permission(self._user_session, "maintenance", scope_id, "maintenance.read", operation_label=operation_label)
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
            require_scope_permission(self._user_session, "maintenance", scope_id, "maintenance.manage", operation_label=operation_label)
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

    def _record_change(self, action: str, row: MaintenancePreventivePlan) -> None:
        record_activity(self, action=action, entity_type="maintenance_preventive_plan", entity_id=row.id,
 module="maintenance", details={
            "organization_id": row.organization_id, "site_id": row.site_id,
            "plan_code": row.plan_code, "name": row.name,
            "asset_id": row.asset_id, "component_id": row.component_id, "system_id": row.system_id,
            "status": row.status.value, "plan_type": row.plan_type.value,
            "trigger_mode": row.trigger_mode.value, "sensor_id": row.sensor_id,
            "auto_generate_work_order": row.auto_generate_work_order, "is_active": row.is_active,
        })
        domain_events.domain_changed.emit(DomainChangeEvent(
            category="module", scope_code="maintenance_management",
            entity_type="maintenance_preventive_plan", entity_id=row.id,
            source_event="maintenance_preventive_plans_changed",
        ))

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.read", operation_label=operation_label)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.manage", operation_label=operation_label)


__all__ = ["MaintenancePreventivePlanService"]
