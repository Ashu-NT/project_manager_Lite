from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from core.modules.maintenance_management.domain import (
    MaintenanceCalendarFrequencyUnit,
    MaintenanceGenerationLeadUnit,
    MaintenancePlanStatus,
    MaintenancePlanTaskTriggerScope,
    MaintenancePreventiveInstanceStatus,
    MaintenancePreventivePlan,
    MaintenancePreventivePlanInstance,
    MaintenancePreventivePlanTask,
    MaintenanceSchedulePolicy,
    MaintenanceSensor,
    MaintenanceSensorDirection,
    MaintenanceSensorQualityState,
    MaintenanceTriggerMode,
)
from core.modules.maintenance_management.interfaces import (
    MaintenancePreventivePlanInstanceRepository,
    MaintenancePreventivePlanRepository,
    MaintenancePreventivePlanTaskRepository,
    MaintenanceSensorRepository,
    MaintenanceTaskStepTemplateRepository,
    MaintenanceTaskTemplateRepository,
)
from core.modules.maintenance_management.services.preventive.work_package import (
    MaintenancePreventiveWorkPackageBuilder,
)
from core.modules.maintenance_management.services.work_order.service import MaintenanceWorkOrderService
from core.modules.maintenance_management.services.work_order_task.service import MaintenanceWorkOrderTaskService
from core.modules.maintenance_management.services.work_order_task_step.service import MaintenanceWorkOrderTaskStepService
from core.modules.maintenance_management.services.work_request.service import MaintenanceWorkRequestService
from core.platform.access.authorization import filter_scope_rows, require_scope_permission
from core.platform.audit.helpers import record_audit
from core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import NotFoundError
from core.platform.common.ids import generate_id
from core.platform.common.interfaces import OrganizationRepository, SiteRepository
from core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from core.platform.org.domain import Organization, Site


@dataclass(frozen=True)
class MaintenancePreventiveDueCandidate:
    plan_id: str
    plan_code: str
    plan_name: str
    due_state: str
    due_reason: str
    generation_target: str
    selected_plan_task_ids: tuple[str, ...] = ()
    blocked_plan_task_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class MaintenancePreventiveGenerationResult:
    plan_id: str
    plan_code: str
    generation_target: str
    generated_work_request_id: str | None = None
    generated_work_order_id: str | None = None
    generated_task_ids: tuple[str, ...] = ()
    generated_step_ids: tuple[str, ...] = ()
    skipped_reason: str = ""


@dataclass(frozen=True)
class MaintenancePreventiveForecastRow:
    instance_id: str
    due_at: datetime
    generation_window_opens_at: datetime
    instance_status: str
    planner_state: str
    generated_work_request_id: str | None = None
    generated_work_order_id: str | None = None
    completed_at: datetime | None = None


@dataclass(frozen=True)
class _TriggerEvaluation:
    due: bool
    blocked: bool
    reason: str
    sensor: MaintenanceSensor | None = None


class MaintenancePreventiveGenerationService:
    def __init__(
        self,
        session: Session,
        *,
        organization_repo: OrganizationRepository,
        site_repo: SiteRepository,
        preventive_plan_instance_repo: MaintenancePreventivePlanInstanceRepository,
        preventive_plan_repo: MaintenancePreventivePlanRepository,
        preventive_plan_task_repo: MaintenancePreventivePlanTaskRepository,
        task_template_repo: MaintenanceTaskTemplateRepository,
        task_step_template_repo: MaintenanceTaskStepTemplateRepository,
        sensor_repo: MaintenanceSensorRepository,
        work_request_service: MaintenanceWorkRequestService,
        work_order_service: MaintenanceWorkOrderService,
        work_order_task_service: MaintenanceWorkOrderTaskService,
        work_order_task_step_service: MaintenanceWorkOrderTaskStepService,
        user_session=None,
        audit_service=None,
    ) -> None:
        self._session = session
        self._organization_repo = organization_repo
        self._site_repo = site_repo
        self._preventive_plan_instance_repo = preventive_plan_instance_repo
        self._preventive_plan_repo = preventive_plan_repo
        self._preventive_plan_task_repo = preventive_plan_task_repo
        self._task_template_repo = task_template_repo
        self._task_step_template_repo = task_step_template_repo
        self._sensor_repo = sensor_repo
        self._work_request_service = work_request_service
        self._work_order_service = work_order_service
        self._work_order_task_service = work_order_task_service
        self._work_order_task_step_service = work_order_task_step_service
        self._work_package_builder = MaintenancePreventiveWorkPackageBuilder(
            task_template_repo=task_template_repo,
            task_step_template_repo=task_step_template_repo,
            work_order_task_service=work_order_task_service,
            work_order_task_step_service=work_order_task_step_service,
        )
        self._user_session = user_session
        self._audit_service = audit_service

    def list_due_candidates(
        self,
        *,
        as_of: datetime | None = None,
        site_id: str | None = None,
        plan_id: str | None = None,
    ) -> list[MaintenancePreventiveDueCandidate]:
        self._require_read("list maintenance preventive due candidates")
        organization = self._active_organization()
        resolved_as_of = self._resolve_as_of(as_of)
        if site_id is not None:
            self._get_site(site_id, organization=organization)
        rows = self._list_visible_active_plans(organization=organization, site_id=site_id, plan_id=plan_id)
        for row in rows:
            self._sync_calendar_plan_instances(row, resolved_as_of)
        return [self._build_candidate(plan, resolved_as_of) for plan in rows]

    def refresh_schedule(
        self,
        *,
        as_of: datetime | None = None,
        site_id: str | None = None,
        plan_id: str | None = None,
    ) -> list[MaintenancePreventivePlanInstance]:
        self._require_manage("refresh maintenance preventive schedule")
        organization = self._active_organization()
        resolved_as_of = self._resolve_as_of(as_of)
        if site_id is not None:
            self._get_site(site_id, organization=organization)
        rows = self._list_visible_active_plans(organization=organization, site_id=site_id, plan_id=plan_id)
        refreshed: list[MaintenancePreventivePlanInstance] = []
        for row in rows:
            self._require_scope_manage(
                self._scope_anchor_for_plan(row),
                operation_label="refresh maintenance preventive schedule",
            )
            refreshed.extend(self._normalize_instances(self._sync_calendar_plan_instances(row, resolved_as_of)))
        return refreshed

    def list_plan_instances(
        self,
        *,
        plan_id: str,
        status: str | None = None,
    ) -> list[MaintenancePreventivePlanInstance]:
        self._require_read("list maintenance preventive schedule instances")
        organization = self._active_organization()
        plan = self._preventive_plan_repo.get(plan_id)
        if plan is None or plan.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance preventive plan not found in the active organization.",
                code="MAINTENANCE_PREVENTIVE_PLAN_NOT_FOUND",
            )
        self._require_scope_read(
            self._scope_anchor_for_plan(plan),
            operation_label="list maintenance preventive schedule instances",
        )
        self._sync_calendar_plan_instances(plan, self._resolve_as_of(None))
        rows = self._preventive_plan_instance_repo.list_for_organization(
            organization.id,
            plan_id=plan.id,
            status=status,
        )
        return self._normalize_instances(rows)

    def preview_plan_schedule(
        self,
        *,
        plan_id: str,
        as_of: datetime | None = None,
    ) -> list[MaintenancePreventiveForecastRow]:
        self._require_read("preview maintenance preventive schedule")
        organization = self._active_organization()
        plan = self._preventive_plan_repo.get(plan_id)
        if plan is None or plan.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance preventive plan not found in the active organization.",
                code="MAINTENANCE_PREVENTIVE_PLAN_NOT_FOUND",
            )
        self._require_scope_read(
            self._scope_anchor_for_plan(plan),
            operation_label="preview maintenance preventive schedule",
        )
        resolved_as_of = self._resolve_as_of(as_of)
        self._sync_calendar_plan_instances(plan, resolved_as_of)
        rows = self._preventive_plan_instance_repo.list_for_organization(
            organization.id,
            plan_id=plan.id,
        )
        return [
            MaintenancePreventiveForecastRow(
                instance_id=row.id,
                due_at=self._resolve_as_of(row.due_at),
                generation_window_opens_at=self._lead_window_starts_at(plan, self._resolve_as_of(row.due_at)),
                instance_status=row.status.value,
                planner_state=self._forecast_planner_state(plan, row, resolved_as_of),
                generated_work_request_id=row.generated_work_request_id,
                generated_work_order_id=row.generated_work_order_id,
                completed_at=self._resolve_as_of(row.completed_at) if row.completed_at is not None else None,
            )
            for row in rows
        ]

    def regenerate_plan_schedule(
        self,
        *,
        plan_id: str,
        as_of: datetime | None = None,
    ) -> list[MaintenancePreventiveForecastRow]:
        self.refresh_schedule(plan_id=plan_id, as_of=as_of)
        return self.preview_plan_schedule(plan_id=plan_id, as_of=as_of)

    def generate_due_work(
        self,
        *,
        as_of: datetime | None = None,
        site_id: str | None = None,
        plan_id: str | None = None,
    ) -> list[MaintenancePreventiveGenerationResult]:
        self._require_manage("generate maintenance preventive work")
        organization = self._active_organization()
        resolved_as_of = self._resolve_as_of(as_of)
        if site_id is not None:
            self._get_site(site_id, organization=organization)
        rows = self._list_visible_active_plans(organization=organization, site_id=site_id, plan_id=plan_id)
        results: list[MaintenancePreventiveGenerationResult] = []
        for plan in rows:
            self._sync_calendar_plan_instances(plan, resolved_as_of)
            candidate = self._build_candidate(plan, resolved_as_of)
            if candidate.due_state != "DUE":
                results.append(
                    MaintenancePreventiveGenerationResult(
                        plan_id=plan.id,
                        plan_code=plan.plan_code,
                        generation_target=candidate.generation_target,
                        skipped_reason=candidate.due_reason,
                    )
                )
                continue
            self._require_scope_manage(
                self._scope_anchor_for_plan(plan),
                operation_label="generate maintenance preventive work",
            )
            results.append(self._generate_candidate(plan, candidate, resolved_as_of))
        return results

    def _generate_candidate(
        self,
        plan: MaintenancePreventivePlan,
        candidate: MaintenancePreventiveDueCandidate,
        as_of: datetime,
    ) -> MaintenancePreventiveGenerationResult:
        due_instance = self._select_due_instance(plan, as_of)
        generated_work_request_id: str | None = None
        generated_work_order_id: str | None = None
        generated_task_ids: list[str] = []
        generated_step_ids: list[str] = []
        target = "WORK_ORDER" if plan.auto_generate_work_order else "WORK_REQUEST"
        selected_plan_tasks = self._selected_plan_tasks(plan.id, candidate)

        if target == "WORK_ORDER":
            work_order = self._work_order_service.create_work_order(
                site_id=plan.site_id,
                work_order_code=self._build_generated_code(plan.plan_code, suffix="WO"),
                work_order_type=self._map_plan_to_work_order_type(plan),
                source_type="PREVENTIVE_PLAN",
                source_id=plan.id,
                asset_id=plan.asset_id,
                component_id=plan.component_id,
                system_id=plan.system_id,
                title=plan.name,
                description=self._build_generation_description(plan, candidate, as_of),
                priority=plan.priority,
                requires_shutdown=plan.requires_shutdown,
                approval_required=plan.approval_required,
                is_preventive=True,
                notes=f"Generated from preventive plan {plan.plan_code}.",
            )
            generated_work_order_id = work_order.id
            generated_package = self._work_package_builder.populate_work_order(
                plan=plan,
                plan_tasks=selected_plan_tasks,
                work_order=work_order,
            )
            generated_task_ids.extend(generated_package.generated_task_ids)
            generated_step_ids.extend(generated_package.generated_step_ids)
        else:
            work_request = self._work_request_service.create_work_request(
                site_id=plan.site_id,
                work_request_code=self._build_generated_code(plan.plan_code, suffix="WR"),
                source_type="PREVENTIVE_PLAN",
                source_id=plan.id,
                source_plan_task_ids=tuple(row.id for row in selected_plan_tasks),
                request_type=plan.plan_type.value,
                asset_id=plan.asset_id,
                component_id=plan.component_id,
                system_id=plan.system_id,
                title=plan.name,
                description=self._build_generation_description(plan, candidate, as_of),
                priority=plan.priority,
                notes=f"Generated from preventive plan {plan.plan_code}.",
            )
            generated_work_request_id = work_request.id

        self._apply_plan_generation_state(
            plan,
            as_of,
            due_instance=due_instance,
            generated_work_request_id=generated_work_request_id,
            generated_work_order_id=generated_work_order_id,
        )
        for plan_task in selected_plan_tasks:
            self._apply_plan_task_generation_state(plan_task, as_of)

        record_audit(
            self,
            action="maintenance.preventive.generate",
            entity_type="maintenance_preventive_plan",
            entity_id=plan.id,
            details={
                "plan_code": plan.plan_code,
                "generation_target": target,
                "generated_work_request_id": generated_work_request_id,
                "generated_work_order_id": generated_work_order_id,
                "generated_task_count": len(generated_task_ids),
                "generated_step_count": len(generated_step_ids),
                "selected_plan_task_ids": list(candidate.selected_plan_task_ids),
            },
        )
        return MaintenancePreventiveGenerationResult(
            plan_id=plan.id,
            plan_code=plan.plan_code,
            generation_target=target,
            generated_work_request_id=generated_work_request_id,
            generated_work_order_id=generated_work_order_id,
            generated_task_ids=tuple(generated_task_ids),
            generated_step_ids=tuple(generated_step_ids),
        )

    def _build_candidate(
        self,
        plan: MaintenancePreventivePlan,
        as_of: datetime,
    ) -> MaintenancePreventiveDueCandidate:
        plan_eval = (
            self._evaluate_calendar_instance_window(plan, as_of)
            if self._plan_uses_calendar_instances(plan)
            else self._evaluate_plan_trigger(plan, as_of)
        )
        plan_tasks = self._preventive_plan_task_repo.list_for_organization(plan.organization_id, plan_id=plan.id)
        selected_ids: list[str] = []
        blocked_ids: list[str] = []

        for plan_task in plan_tasks:
            if plan_task.trigger_scope == MaintenancePlanTaskTriggerScope.INHERIT_PLAN:
                if plan_eval.due:
                    selected_ids.append(plan_task.id)
                continue
            task_eval = self._evaluate_plan_task_trigger(plan, plan_task, as_of)
            if task_eval.due:
                selected_ids.append(plan_task.id)
            elif task_eval.blocked:
                blocked_ids.append(plan_task.id)

        if plan_eval.due and plan_tasks and not selected_ids:
            return MaintenancePreventiveDueCandidate(
                plan_id=plan.id,
                plan_code=plan.plan_code,
                plan_name=plan.name,
                due_state="NOT_DUE",
                due_reason="Plan is due, but no plan tasks are currently due.",
                generation_target="WORK_ORDER" if plan.auto_generate_work_order else "WORK_REQUEST",
                blocked_plan_task_ids=tuple(blocked_ids),
            )
        if plan_eval.due or selected_ids:
            return MaintenancePreventiveDueCandidate(
                plan_id=plan.id,
                plan_code=plan.plan_code,
                plan_name=plan.name,
                due_state="DUE",
                due_reason=plan_eval.reason if plan_eval.due else "One or more task-level trigger overrides are due.",
                generation_target="WORK_ORDER" if plan.auto_generate_work_order else "WORK_REQUEST",
                selected_plan_task_ids=tuple(selected_ids),
                blocked_plan_task_ids=tuple(blocked_ids),
            )
        if plan_eval.blocked:
            return MaintenancePreventiveDueCandidate(
                plan_id=plan.id,
                plan_code=plan.plan_code,
                plan_name=plan.name,
                due_state="BLOCKED",
                due_reason=plan_eval.reason,
                generation_target="WORK_ORDER" if plan.auto_generate_work_order else "WORK_REQUEST",
                blocked_plan_task_ids=tuple(blocked_ids),
            )
        return MaintenancePreventiveDueCandidate(
            plan_id=plan.id,
            plan_code=plan.plan_code,
            plan_name=plan.name,
            due_state="NOT_DUE",
            due_reason=plan_eval.reason or "Preventive plan is not due.",
            generation_target="WORK_ORDER" if plan.auto_generate_work_order else "WORK_REQUEST",
            blocked_plan_task_ids=tuple(blocked_ids),
        )

    def _sync_calendar_plan_instances(
        self,
        plan: MaintenancePreventivePlan,
        as_of: datetime,
    ) -> list[MaintenancePreventivePlanInstance]:
        if not self._plan_uses_calendar_instances(plan):
            return self._preventive_plan_instance_repo.list_for_organization(
                plan.organization_id,
                plan_id=plan.id,
            )
        rows = self._preventive_plan_instance_repo.list_for_organization(
            plan.organization_id,
            plan_id=plan.id,
        )
        planned_by_due = {
            self._resolve_as_of(row.due_at): row
            for row in rows
            if row.status == MaintenancePreventiveInstanceStatus.PLANNED
        }
        desired_due_dates = self._build_planned_due_dates(plan, as_of)
        desired_instances: list[MaintenancePreventivePlanInstance] = []
        changed = False
        for due_at in desired_due_dates:
            existing = planned_by_due.pop(due_at, None)
            if existing is not None:
                desired_instances.append(existing)
                continue
            instance = MaintenancePreventivePlanInstance.create(
                organization_id=plan.organization_id,
                plan_id=plan.id,
                due_at=due_at,
                notes=f"Planned schedule instance for preventive plan {plan.plan_code}.",
            )
            self._preventive_plan_instance_repo.add(instance)
            desired_instances.append(instance)
            changed = True
        for orphan in planned_by_due.values():
            self._preventive_plan_instance_repo.delete(orphan.id)
            changed = True
        next_due_at = desired_instances[0].due_at if desired_instances else None
        if plan.next_due_at != next_due_at:
            plan.next_due_at = next_due_at
            plan.updated_at = as_of
            self._preventive_plan_repo.update(plan)
            changed = True
        if changed:
            self._session.commit()
        return self._normalize_instances(self._preventive_plan_instance_repo.list_for_organization(
            plan.organization_id,
            plan_id=plan.id,
        ))

    def _build_planned_due_dates(
        self,
        plan: MaintenancePreventivePlan,
        as_of: datetime,
    ) -> list[datetime]:
        if plan.calendar_frequency_unit is None or plan.calendar_frequency_value in (None, 0):
            return []
        start_due = self._resolve_as_of(plan.next_due_at) if plan.next_due_at is not None else None
        if start_due is None:
            start_due = self._advance_calendar_due(
                as_of,
                plan.calendar_frequency_unit,
                plan.calendar_frequency_value,
            )
        planned_due_dates: list[datetime] = []
        current_due = start_due
        for _ in range(max(plan.generation_horizon_count, 1)):
            planned_due_dates.append(current_due)
            current_due = self._advance_calendar_due(
                current_due,
                plan.calendar_frequency_unit,
                plan.calendar_frequency_value,
            )
        return planned_due_dates

    def _select_due_instance(
        self,
        plan: MaintenancePreventivePlan,
        as_of: datetime,
    ) -> MaintenancePreventivePlanInstance | None:
        if not self._plan_uses_calendar_instances(plan):
            return None
        for row in self._preventive_plan_instance_repo.list_for_organization(
            plan.organization_id,
            plan_id=plan.id,
            status=MaintenancePreventiveInstanceStatus.PLANNED.value,
        ):
            if as_of >= self._lead_window_starts_at(plan, self._resolve_as_of(row.due_at)):
                return row
        return None

    def _evaluate_calendar_instance_window(
        self,
        plan: MaintenancePreventivePlan,
        as_of: datetime,
    ) -> _TriggerEvaluation:
        rows = self._preventive_plan_instance_repo.list_for_organization(
            plan.organization_id,
            plan_id=plan.id,
            status=MaintenancePreventiveInstanceStatus.PLANNED.value,
        )
        if not rows:
            return _TriggerEvaluation(
                due=False,
                blocked=True,
                reason="Preventive plan has no planned schedule instances to generate from.",
            )
        next_instance = rows[0]
        due_at = self._resolve_as_of(next_instance.due_at)
        window_opens_at = self._lead_window_starts_at(plan, due_at)
        if as_of >= due_at:
            return _TriggerEvaluation(
                due=True,
                blocked=False,
                reason=f"Preventive plan reached its scheduled due date on {due_at.isoformat()}.",
            )
        if as_of >= window_opens_at:
            if window_opens_at == due_at:
                return _TriggerEvaluation(
                    due=True,
                    blocked=False,
                    reason="Preventive plan reached its generation window on the due date.",
                )
            return _TriggerEvaluation(
                due=True,
                blocked=False,
                reason=(
                    "Preventive plan entered its lead generation window "
                    f"on {window_opens_at.isoformat()} for scheduled due date {due_at.isoformat()}."
                ),
            )
        return _TriggerEvaluation(
            due=False,
            blocked=False,
            reason=(
                f"Preventive plan is scheduled for {due_at.isoformat()}; "
                f"generation window opens at {window_opens_at.isoformat()}."
            ),
        )

    def _plan_uses_calendar_instances(self, plan: MaintenancePreventivePlan) -> bool:
        return (
            plan.trigger_mode == MaintenanceTriggerMode.CALENDAR
            and plan.calendar_frequency_unit is not None
            and plan.calendar_frequency_value not in (None, 0)
        )

    def _selected_plan_tasks(
        self,
        plan_id: str,
        candidate: MaintenancePreventiveDueCandidate,
    ) -> list[MaintenancePreventivePlanTask]:
        selected = set(candidate.selected_plan_task_ids)
        if not selected:
            return []
        rows = self._preventive_plan_task_repo.list_for_organization(
            self._active_organization().id,
            plan_id=plan_id,
        )
        return [row for row in rows if row.id in selected]

    def _evaluate_plan_trigger(self, plan: MaintenancePreventivePlan, as_of: datetime) -> _TriggerEvaluation:
        return self._evaluate_trigger_state(
            trigger_mode=plan.trigger_mode,
            calendar_frequency_unit=plan.calendar_frequency_unit,
            calendar_frequency_value=plan.calendar_frequency_value,
            sensor_id=plan.sensor_id,
            sensor_threshold=plan.sensor_threshold,
            sensor_direction=plan.sensor_direction,
            last_generated_at=plan.last_generated_at,
            next_due_at=plan.next_due_at,
            next_due_counter=plan.next_due_counter,
            as_of=as_of,
        )

    def _evaluate_plan_task_trigger(
        self,
        plan: MaintenancePreventivePlan,
        plan_task: MaintenancePreventivePlanTask,
        as_of: datetime,
    ) -> _TriggerEvaluation:
        return self._evaluate_trigger_state(
            trigger_mode=plan_task.trigger_mode_override,
            calendar_frequency_unit=plan_task.calendar_frequency_unit_override,
            calendar_frequency_value=plan_task.calendar_frequency_value_override,
            sensor_id=plan_task.sensor_id_override,
            sensor_threshold=plan_task.sensor_threshold_override,
            sensor_direction=plan_task.sensor_direction_override,
            last_generated_at=plan_task.last_generated_at,
            next_due_at=plan_task.next_due_at,
            next_due_counter=plan_task.next_due_counter,
            as_of=as_of,
        )

    def _evaluate_trigger_state(
        self,
        *,
        trigger_mode,
        calendar_frequency_unit,
        calendar_frequency_value: int | None,
        sensor_id: str | None,
        sensor_threshold: Decimal | None,
        sensor_direction,
        last_generated_at: datetime | None,
        next_due_at: datetime | None,
        next_due_counter: Decimal | None,
        as_of: datetime,
    ) -> _TriggerEvaluation:
        if trigger_mode == MaintenanceTriggerMode.CALENDAR:
            return self._evaluate_calendar_trigger(
                calendar_frequency_unit=calendar_frequency_unit,
                calendar_frequency_value=calendar_frequency_value,
                last_generated_at=last_generated_at,
                next_due_at=next_due_at,
                as_of=as_of,
            )
        sensor_eval = self._evaluate_sensor_trigger(
            sensor_id=sensor_id,
            sensor_threshold=sensor_threshold,
            sensor_direction=sensor_direction,
            last_generated_at=last_generated_at,
            next_due_counter=next_due_counter,
        )
        if trigger_mode == MaintenanceTriggerMode.SENSOR:
            return sensor_eval
        if sensor_eval.blocked:
            return _TriggerEvaluation(
                due=False,
                blocked=True,
                reason="Hybrid trigger is blocked because the linked sensor state is not usable.",
                sensor=sensor_eval.sensor,
            )
        if sensor_eval.due:
            return _TriggerEvaluation(
                due=True,
                blocked=False,
                reason="Hybrid preventive trigger is due from sensor state.",
                sensor=sensor_eval.sensor,
            )
        calendar_eval = self._evaluate_calendar_trigger(
            calendar_frequency_unit=calendar_frequency_unit,
            calendar_frequency_value=calendar_frequency_value,
            last_generated_at=last_generated_at,
            next_due_at=next_due_at,
            as_of=as_of,
        )
        if calendar_eval.due:
            return _TriggerEvaluation(
                due=True,
                blocked=False,
                reason="Hybrid preventive trigger is due from calendar cadence.",
                sensor=sensor_eval.sensor,
            )
        return _TriggerEvaluation(
            due=False,
            blocked=False,
            reason="Hybrid preventive trigger is not due.",
            sensor=sensor_eval.sensor,
        )

    def _evaluate_calendar_trigger(
        self,
        *,
        calendar_frequency_unit,
        calendar_frequency_value: int | None,
        last_generated_at: datetime | None,
        next_due_at: datetime | None,
        as_of: datetime,
    ) -> _TriggerEvaluation:
        if calendar_frequency_unit is None or calendar_frequency_value in (None, 0):
            return _TriggerEvaluation(
                due=False,
                blocked=True,
                reason="Calendar trigger configuration is incomplete.",
            )
        effective_next_due = next_due_at
        if effective_next_due is not None:
            effective_next_due = self._resolve_as_of(effective_next_due)
        if effective_next_due is None and last_generated_at is not None:
            effective_next_due = self._advance_calendar_due(
                self._resolve_as_of(last_generated_at),
                calendar_frequency_unit,
                calendar_frequency_value,
            )
        if effective_next_due is None:
            return _TriggerEvaluation(
                due=True,
                blocked=False,
                reason="Preventive plan is due because no previous generation exists.",
            )
        if as_of >= effective_next_due:
            return _TriggerEvaluation(
                due=True,
                blocked=False,
                reason="Preventive plan reached its calendar due date.",
            )
        return _TriggerEvaluation(
            due=False,
            blocked=False,
            reason="Preventive plan has not reached its calendar due date.",
        )

    def _evaluate_sensor_trigger(
        self,
        *,
        sensor_id: str | None,
        sensor_threshold: Decimal | None,
        sensor_direction,
        last_generated_at: datetime | None,
        next_due_counter: Decimal | None,
    ) -> _TriggerEvaluation:
        if not sensor_id or sensor_threshold is None or sensor_direction is None:
            return _TriggerEvaluation(due=False, blocked=True, reason="Sensor trigger configuration is incomplete.")
        sensor = self._sensor_repo.get(sensor_id)
        if sensor is None:
            return _TriggerEvaluation(due=False, blocked=True, reason="Linked preventive sensor was not found.")
        if sensor.current_value is None or sensor.last_read_at is None:
            return _TriggerEvaluation(due=False, blocked=True, reason="Linked preventive sensor has no usable reading.", sensor=sensor)
        if sensor.last_quality_state != MaintenanceSensorQualityState.VALID:
            return _TriggerEvaluation(due=False, blocked=True, reason="Linked preventive sensor is not in a valid quality state.", sensor=sensor)
        if sensor_direction == MaintenanceSensorDirection.GREATER_OR_EQUAL:
            trigger_value = next_due_counter if next_due_counter is not None else sensor_threshold
            if sensor.current_value >= trigger_value:
                return _TriggerEvaluation(due=True, blocked=False, reason="Sensor threshold reached.", sensor=sensor)
            return _TriggerEvaluation(due=False, blocked=False, reason="Sensor threshold not yet reached.", sensor=sensor)
        if last_generated_at is not None and sensor.last_read_at <= last_generated_at:
            return _TriggerEvaluation(due=False, blocked=False, reason="No newer qualifying sensor reading is available.", sensor=sensor)
        if sensor_direction == MaintenanceSensorDirection.LESS_OR_EQUAL:
            due = sensor.current_value <= sensor_threshold
        else:
            due = sensor.current_value == sensor_threshold
        return _TriggerEvaluation(
            due=due,
            blocked=False,
            reason="Sensor threshold reached." if due else "Sensor threshold not yet reached.",
            sensor=sensor,
        )

    def _apply_plan_generation_state(
        self,
        plan: MaintenancePreventivePlan,
        as_of: datetime,
        *,
        due_instance: MaintenancePreventivePlanInstance | None,
        generated_work_request_id: str | None,
        generated_work_order_id: str | None,
    ) -> None:
        sensor = self._sensor_repo.get(plan.sensor_id) if plan.sensor_id else None
        plan.last_generated_at = as_of
        if due_instance is not None:
            due_instance.status = MaintenancePreventiveInstanceStatus.GENERATED
            due_instance.generated_at = as_of
            due_instance.generated_work_request_id = generated_work_request_id
            due_instance.generated_work_order_id = generated_work_order_id
            due_instance.updated_at = as_of
            self._preventive_plan_instance_repo.update(due_instance)
            remaining_planned = self._preventive_plan_instance_repo.list_for_organization(
                plan.organization_id,
                plan_id=plan.id,
                status=MaintenancePreventiveInstanceStatus.PLANNED.value,
            )
            plan.next_due_at = remaining_planned[0].due_at if remaining_planned else None
        else:
            plan.next_due_at = self._next_calendar_due_value(
                as_of,
                plan.calendar_frequency_unit,
                plan.calendar_frequency_value,
            )
        plan.next_due_counter = self._next_sensor_due_counter(
            sensor=sensor,
            threshold=plan.sensor_threshold,
            direction=plan.sensor_direction,
            current_due_counter=plan.next_due_counter,
        )
        plan.updated_at = as_of
        self._preventive_plan_repo.update(plan)
        self._session.commit()
        if due_instance is not None and self._plan_uses_calendar_instances(plan):
            self._sync_calendar_plan_instances(plan, as_of)
        domain_events.domain_changed.emit(
            DomainChangeEvent(
                category="module",
                scope_code="maintenance_management",
                entity_type="maintenance_preventive_plan",
                entity_id=plan.id,
                source_event="maintenance_preventive_plans_changed",
            )
        )

    def _apply_plan_task_generation_state(
        self,
        plan_task: MaintenancePreventivePlanTask,
        as_of: datetime,
    ) -> None:
        sensor = self._sensor_repo.get(plan_task.sensor_id_override) if plan_task.sensor_id_override else None
        plan_task.last_generated_at = as_of
        plan_task.next_due_at = self._next_calendar_due_value(
            as_of,
            plan_task.calendar_frequency_unit_override,
            plan_task.calendar_frequency_value_override,
        )
        plan_task.next_due_counter = self._next_sensor_due_counter(
            sensor=sensor,
            threshold=plan_task.sensor_threshold_override,
            direction=plan_task.sensor_direction_override,
            current_due_counter=plan_task.next_due_counter,
        )
        plan_task.updated_at = as_of
        self._preventive_plan_task_repo.update(plan_task)
        self._session.commit()
        domain_events.domain_changed.emit(
            DomainChangeEvent(
                category="module",
                scope_code="maintenance_management",
                entity_type="maintenance_preventive_plan_task",
                entity_id=plan_task.id,
                source_event="maintenance_preventive_plan_tasks_changed",
            )
        )

    def _next_calendar_due_value(
        self,
        as_of: datetime,
        unit: MaintenanceCalendarFrequencyUnit | None,
        value: int | None,
    ) -> datetime | None:
        if unit is None or value in (None, 0):
            return None
        return self._advance_calendar_due(as_of, unit, value)

    def _next_sensor_due_counter(
        self,
        *,
        sensor: MaintenanceSensor | None,
        threshold: Decimal | None,
        direction: MaintenanceSensorDirection | None,
        current_due_counter: Decimal | None,
    ) -> Decimal | None:
        if sensor is None or sensor.current_value is None or threshold is None or direction is None:
            return None
        if direction == MaintenanceSensorDirection.GREATER_OR_EQUAL:
            base_value = current_due_counter if current_due_counter is not None else threshold
            while sensor.current_value >= base_value:
                base_value += threshold
            return base_value
        return current_due_counter

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
        return self._add_months(anchor, months)

    def _lead_window_starts_at(
        self,
        plan: MaintenancePreventivePlan,
        due_at: datetime,
    ) -> datetime:
        lead_value = max(int(getattr(plan, "generation_lead_value", 0) or 0), 0)
        if lead_value == 0:
            return due_at
        lead_unit = getattr(plan, "generation_lead_unit", MaintenanceGenerationLeadUnit.DAYS)
        if lead_unit == MaintenanceGenerationLeadUnit.DAYS:
            return due_at - timedelta(days=lead_value)
        if lead_unit == MaintenanceGenerationLeadUnit.WEEKS:
            return due_at - timedelta(weeks=lead_value)
        return self._add_months(due_at, -lead_value)

    def _forecast_planner_state(
        self,
        plan: MaintenancePreventivePlan,
        row: MaintenancePreventivePlanInstance,
        as_of: datetime,
    ) -> str:
        if row.status == MaintenancePreventiveInstanceStatus.COMPLETED:
            return "COMPLETED"
        if row.status == MaintenancePreventiveInstanceStatus.GENERATED:
            return "GENERATED"
        if row.status == MaintenancePreventiveInstanceStatus.CANCELLED:
            return "CANCELLED"
        due_at = self._resolve_as_of(row.due_at)
        window_opens_at = self._lead_window_starts_at(plan, due_at)
        if as_of >= due_at:
            return "DUE"
        if as_of >= window_opens_at:
            return "READY_WINDOW"
        return "UPCOMING"

    def _add_months(self, anchor: datetime, months: int) -> datetime:
        total_month = anchor.month - 1 + months
        year = anchor.year + total_month // 12
        month = total_month % 12 + 1
        day = min(anchor.day, monthrange(year, month)[1])
        return anchor.replace(year=year, month=month, day=day)

    def _map_plan_to_work_order_type(self, plan: MaintenancePreventivePlan) -> str:
        mapping = {
            "PREVENTIVE": "PREVENTIVE",
            "INSPECTION": "INSPECTION",
            "CALIBRATION": "CALIBRATION",
            "LUBRICATION": "PREVENTIVE",
            "CONDITION_BASED": "CONDITION_BASED",
        }
        return mapping.get(plan.plan_type.value, "PREVENTIVE")

    def _build_generation_description(
        self,
        plan: MaintenancePreventivePlan,
        candidate: MaintenancePreventiveDueCandidate,
        as_of: datetime,
    ) -> str:
        return (
            f"Generated from preventive plan {plan.plan_code} on {as_of.isoformat()}."
            f" Trigger reason: {candidate.due_reason}"
        )

    def _build_generated_code(self, base_code: str, *, suffix: str) -> str:
        token = generate_id().replace("-", "")[:8].upper()
        return f"{base_code}-{suffix}-{token}"

    def _list_visible_active_plans(
        self,
        *,
        organization: Organization,
        site_id: str | None,
        plan_id: str | None,
    ) -> list[MaintenancePreventivePlan]:
        rows = self._preventive_plan_repo.list_for_organization(
            organization.id,
            active_only=True,
            site_id=site_id,
            status=MaintenancePlanStatus.ACTIVE,
        )
        if plan_id is not None:
            rows = [row for row in rows if row.id == plan_id]
        return filter_scope_rows(
            rows,
            self._user_session,
            scope_type="maintenance",
            permission_code="maintenance.read",
            scope_id_getter=self._scope_anchor_for_plan,
        )

    def _scope_anchor_for_plan(self, row: MaintenancePreventivePlan) -> str:
        if row.asset_id:
            return row.asset_id
        if row.component_id:
            return row.component_id
        if row.system_id:
            return row.system_id
        return ""

    def _resolve_as_of(self, as_of: datetime | None) -> datetime:
        if as_of is None:
            return datetime.now(timezone.utc)
        if as_of.tzinfo is None:
            return as_of.replace(tzinfo=timezone.utc)
        return as_of.astimezone(timezone.utc)

    def _active_organization(self) -> Organization:
        organization = self._organization_repo.get_active()
        if organization is None:
            raise NotFoundError("Active organization not found.", code="ORGANIZATION_NOT_FOUND")
        return organization

    def _get_site(self, site_id: str, *, organization: Organization) -> Site:
        row = self._site_repo.get(site_id)
        if row is None or row.organization_id != organization.id:
            raise NotFoundError("Site not found in the active organization.", code="SITE_NOT_FOUND")
        return row

    def _normalize_instances(
        self,
        rows: list[MaintenancePreventivePlanInstance],
    ) -> list[MaintenancePreventivePlanInstance]:
        for row in rows:
            row.due_at = self._resolve_as_of(row.due_at)
            if row.generated_at is not None:
                row.generated_at = self._resolve_as_of(row.generated_at)
            if row.completed_at is not None:
                row.completed_at = self._resolve_as_of(row.completed_at)
        return rows

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.read", operation_label=operation_label)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.manage", operation_label=operation_label)

    def _require_scope_read(self, scope_id: str, *, operation_label: str) -> None:
        require_scope_permission(
            self._user_session,
            "maintenance",
            scope_id,
            "maintenance.read",
            operation_label=operation_label,
        )

    def _require_scope_manage(self, scope_id: str, *, operation_label: str) -> None:
        require_scope_permission(
            self._user_session,
            "maintenance",
            scope_id,
            "maintenance.manage",
            operation_label=operation_label,
        )


__all__ = [
    "MaintenancePreventiveDueCandidate",
    "MaintenancePreventiveGenerationResult",
    "MaintenancePreventiveGenerationService",
]
