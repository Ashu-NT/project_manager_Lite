"""Preventive generation service — orchestrates due-detection and work generation."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from src.core.modules.maintenance.domain import (
    MaintenancePreventiveInstanceStatus,
    MaintenancePlanStatus,
    MaintenancePlanTaskTriggerScope,
    MaintenancePreventivePlan,
    MaintenancePreventivePlanInstance,
    MaintenancePreventivePlanTask,
)
from src.core.modules.maintenance.contracts.repositories import (
    MaintenanceBlackoutWindowRepository,
    MaintenancePreventivePlanInstanceRepository,
    MaintenancePreventivePlanRepository,
    MaintenancePreventivePlanTaskRepository,
    MaintenanceSensorRepository,
    MaintenanceTaskStepTemplateRepository,
    MaintenanceTaskTemplateRepository,
)
from src.core.modules.maintenance.application.work_orders.work_order_service import (
    MaintenanceWorkOrderService,
)
from src.core.modules.maintenance.application.work_orders.work_order_task_service import (
    MaintenanceWorkOrderTaskService,
)
from src.core.modules.maintenance.application.work_orders.work_order_task_step_service import (
    MaintenanceWorkOrderTaskStepService,
)
from src.core.modules.maintenance.application.work_requests.work_request_service import (
    MaintenanceWorkRequestService,
)
from src.core.modules.maintenance.application.preventive.models.candidates import (
    MaintenancePreventiveDueCandidate,
)
from src.core.modules.maintenance.application.preventive.models.results import (
    MaintenancePreventiveForecastRow,
    MaintenancePreventiveGenerationResult,
)
from src.core.modules.maintenance.application.preventive.evaluators.calendar_evaluator import (
    evaluate_calendar_instance_window,
)
from src.core.modules.maintenance.application.preventive.evaluators.trigger_evaluator import (
    evaluate_plan_task_trigger,
    evaluate_plan_trigger,
)
from src.core.modules.maintenance.application.preventive.schedulers.forecast import (
    forecast_planner_state,
)
from src.core.modules.maintenance.application.preventive.schedulers.instance_scheduler import (
    PreventiveInstanceScheduler,
)
from src.core.modules.maintenance.application.preventive.services.work_package import (
    MaintenancePreventiveWorkPackageBuilder,
)
from src.core.modules.maintenance.application.preventive.utils.code_utils import (
    build_generated_code,
    build_generation_description,
    map_plan_to_work_order_type,
)
from src.core.modules.maintenance.application.preventive.utils.date_utils import (
    lead_window_starts_at,
    next_calendar_due_value,
    next_sensor_due_counter,
    resolve_as_of,
)
from src.core.platform.access.authorization import filter_scope_rows, require_scope_permission
from src.core.platform.audit.helpers import record_audit
from src.core.platform.auth.authorization import require_permission
from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.org.contracts import OrganizationRepository, SiteRepository
from src.core.shared.events.domain_events import DomainChangeEvent, domain_events
from src.core.platform.org.domain import Organization, Site


class MaintenancePreventiveGenerationService:
    """
    Orchestrates preventive maintenance due-detection and work generation.

    Delegates to:
    - evaluators  — determine whether a plan or task trigger is due
    - schedulers  — manage planned instances and forecast state
    - utils       — date arithmetic and code generation
    """

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
        blackout_window_repo: MaintenanceBlackoutWindowRepository | None = None,
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
        self._user_session = user_session
        self._audit_service = audit_service
        self._scheduler = PreventiveInstanceScheduler(
            session,
            instance_repo=preventive_plan_instance_repo,
            plan_repo=preventive_plan_repo,
            blackout_window_repo=blackout_window_repo,
        )
        self._work_package_builder = MaintenancePreventiveWorkPackageBuilder(
            task_template_repo=task_template_repo,
            task_step_template_repo=task_step_template_repo,
            work_order_task_service=work_order_task_service,
            work_order_task_step_service=work_order_task_step_service,
        )

    # ------------------------------------------------------------------
    # Public use-case methods
    # ------------------------------------------------------------------

    def list_due_candidates(
        self,
        *,
        as_of: datetime | None = None,
        site_id: str | None = None,
        plan_id: str | None = None,
    ) -> list[MaintenancePreventiveDueCandidate]:
        self._require_read("list maintenance preventive due candidates")
        organization = self._active_organization()
        resolved_as_of = resolve_as_of(as_of)
        if site_id is not None:
            self._get_site(site_id, organization=organization)
        rows = self._list_visible_active_plans(organization=organization, site_id=site_id, plan_id=plan_id)
        for row in rows:
            self._scheduler.sync_calendar_plan_instances(row, resolved_as_of)
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
        resolved_as_of = resolve_as_of(as_of)
        if site_id is not None:
            self._get_site(site_id, organization=organization)
        rows = self._list_visible_active_plans(organization=organization, site_id=site_id, plan_id=plan_id)
        refreshed: list[MaintenancePreventivePlanInstance] = []
        for row in rows:
            self._require_scope_manage(
                self._scope_anchor_for_plan(row),
                operation_label="refresh maintenance preventive schedule",
            )
            refreshed.extend(self._scheduler.sync_calendar_plan_instances(row, resolved_as_of))
        return refreshed

    def list_plan_instances(
        self,
        *,
        plan_id: str,
        status: str | None = None,
    ) -> list[MaintenancePreventivePlanInstance]:
        self._require_read("list maintenance preventive schedule instances")
        organization = self._active_organization()
        plan = self._get_plan(plan_id, organization=organization)
        self._require_scope_read(
            self._scope_anchor_for_plan(plan),
            operation_label="list maintenance preventive schedule instances",
        )
        self._scheduler.sync_calendar_plan_instances(plan, resolve_as_of(None))
        return self._scheduler.list_instances(plan, status=status)

    def preview_plan_schedule(
        self,
        *,
        plan_id: str,
        as_of: datetime | None = None,
    ) -> list[MaintenancePreventiveForecastRow]:
        self._require_read("preview maintenance preventive schedule")
        organization = self._active_organization()
        plan = self._get_plan(plan_id, organization=organization)
        self._require_scope_read(
            self._scope_anchor_for_plan(plan),
            operation_label="preview maintenance preventive schedule",
        )
        resolved_as_of = resolve_as_of(as_of)
        self._scheduler.sync_calendar_plan_instances(plan, resolved_as_of)
        rows = self._scheduler.list_instances(plan)
        return [
            MaintenancePreventiveForecastRow(
                instance_id=row.id,
                due_at=resolve_as_of(row.due_at),
                generation_window_opens_at=lead_window_starts_at(plan, resolve_as_of(row.due_at)),
                instance_status=row.status.value,
                planner_state=forecast_planner_state(plan, row, resolved_as_of),
                generated_work_request_id=row.generated_work_request_id,
                generated_work_order_id=row.generated_work_order_id,
                completed_at=resolve_as_of(row.completed_at) if row.completed_at is not None else None,
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
        resolved_as_of = resolve_as_of(as_of)
        if site_id is not None:
            self._get_site(site_id, organization=organization)
        rows = self._list_visible_active_plans(organization=organization, site_id=site_id, plan_id=plan_id)
        results: list[MaintenancePreventiveGenerationResult] = []
        for plan in rows:
            self._scheduler.sync_calendar_plan_instances(plan, resolved_as_of)
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

    # ------------------------------------------------------------------
    # Internal orchestration
    # ------------------------------------------------------------------

    def _build_candidate(
        self,
        plan: MaintenancePreventivePlan,
        as_of: datetime,
    ) -> MaintenancePreventiveDueCandidate:
        if self._scheduler.plan_uses_calendar_instances(plan):
            instances = self._scheduler.list_instances(
                plan, status=MaintenancePreventiveInstanceStatus.PLANNED.value
            )
            plan_eval = evaluate_calendar_instance_window(
                plan=plan, instances=instances, as_of=as_of
            )
        else:
            sensor = self._sensor_repo.get(plan.sensor_id) if plan.sensor_id else None
            plan_eval = evaluate_plan_trigger(plan, sensor=sensor, as_of=as_of)

        plan_tasks = self._preventive_plan_task_repo.list_for_organization(
            plan.organization_id, plan_id=plan.id
        )
        selected_ids: list[str] = []
        blocked_ids: list[str] = []
        target = "WORK_ORDER" if plan.auto_generate_work_order else "WORK_REQUEST"

        for plan_task in plan_tasks:
            if plan_task.trigger_scope == MaintenancePlanTaskTriggerScope.INHERIT_PLAN:
                if plan_eval.due:
                    selected_ids.append(plan_task.id)
                continue
            task_sensor = (
                self._sensor_repo.get(plan_task.sensor_id_override)
                if plan_task.sensor_id_override
                else None
            )
            task_eval = evaluate_plan_task_trigger(plan_task, sensor=task_sensor, as_of=as_of)
            if task_eval.due:
                selected_ids.append(plan_task.id)
            elif task_eval.blocked:
                blocked_ids.append(plan_task.id)

        if plan_eval.due and plan_tasks and not selected_ids:
            return MaintenancePreventiveDueCandidate(
                plan_id=plan.id, plan_code=plan.plan_code, plan_name=plan.name,
                due_state="NOT_DUE",
                due_reason="Plan is due, but no plan tasks are currently due.",
                generation_target=target,
                blocked_plan_task_ids=tuple(blocked_ids),
            )
        if plan_eval.due or selected_ids:
            return MaintenancePreventiveDueCandidate(
                plan_id=plan.id, plan_code=plan.plan_code, plan_name=plan.name,
                due_state="DUE",
                due_reason=plan_eval.reason if plan_eval.due else "One or more task-level trigger overrides are due.",
                generation_target=target,
                selected_plan_task_ids=tuple(selected_ids),
                blocked_plan_task_ids=tuple(blocked_ids),
            )
        if plan_eval.blocked:
            return MaintenancePreventiveDueCandidate(
                plan_id=plan.id, plan_code=plan.plan_code, plan_name=plan.name,
                due_state="BLOCKED", due_reason=plan_eval.reason,
                generation_target=target,
                blocked_plan_task_ids=tuple(blocked_ids),
            )
        return MaintenancePreventiveDueCandidate(
            plan_id=plan.id, plan_code=plan.plan_code, plan_name=plan.name,
            due_state="NOT_DUE",
            due_reason=plan_eval.reason or "Preventive plan is not due.",
            generation_target=target,
            blocked_plan_task_ids=tuple(blocked_ids),
        )

    def _generate_candidate(
        self,
        plan: MaintenancePreventivePlan,
        candidate: MaintenancePreventiveDueCandidate,
        as_of: datetime,
    ) -> MaintenancePreventiveGenerationResult:
        due_instance = self._scheduler.select_due_instance(plan, as_of)
        target = "WORK_ORDER" if plan.auto_generate_work_order else "WORK_REQUEST"
        selected_plan_tasks = self._selected_plan_tasks(plan.id, candidate)
        generated_work_request_id: str | None = None
        generated_work_order_id: str | None = None
        generated_task_ids: list[str] = []
        generated_step_ids: list[str] = []

        if target == "WORK_ORDER":
            work_order = self._work_order_service.create_work_order(
                site_id=plan.site_id,
                work_order_code=build_generated_code(plan.plan_code, suffix="WO"),
                work_order_type=map_plan_to_work_order_type(plan),
                source_type="PREVENTIVE_PLAN",
                source_id=plan.id,
                asset_id=plan.asset_id,
                component_id=plan.component_id,
                system_id=plan.system_id,
                title=plan.name,
                description=build_generation_description(plan, candidate, as_of),
                priority=plan.priority,
                requires_shutdown=plan.requires_shutdown,
                approval_required=plan.approval_required,
                is_preventive=True,
                notes=f"Generated from preventive plan {plan.plan_code}.",
            )
            generated_work_order_id = work_order.id
            package = self._work_package_builder.populate_work_order(
                plan=plan, plan_tasks=selected_plan_tasks, work_order=work_order
            )
            generated_task_ids.extend(package.generated_task_ids)
            generated_step_ids.extend(package.generated_step_ids)
        else:
            work_request = self._work_request_service.create_work_request(
                site_id=plan.site_id,
                work_request_code=build_generated_code(plan.plan_code, suffix="WR"),
                source_type="PREVENTIVE_PLAN",
                source_id=plan.id,
                source_plan_task_ids=tuple(row.id for row in selected_plan_tasks),
                request_type=plan.plan_type.value,
                asset_id=plan.asset_id,
                component_id=plan.component_id,
                system_id=plan.system_id,
                title=plan.name,
                description=build_generation_description(plan, candidate, as_of),
                priority=plan.priority,
                notes=f"Generated from preventive plan {plan.plan_code}.",
            )
            generated_work_request_id = work_request.id

        self._apply_plan_generation_state(
            plan, as_of,
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
            remaining = self._preventive_plan_instance_repo.list_for_organization(
                plan.organization_id, plan_id=plan.id,
                status=MaintenancePreventiveInstanceStatus.PLANNED.value,
            )
            plan.next_due_at = remaining[0].due_at if remaining else None
        else:
            plan.next_due_at = next_calendar_due_value(
                as_of, plan.calendar_frequency_unit, plan.calendar_frequency_value
            )
        plan.next_due_counter = next_sensor_due_counter(
            sensor=sensor,
            threshold=plan.sensor_threshold,
            direction=plan.sensor_direction,
            current_due_counter=plan.next_due_counter,
        )
        plan.updated_at = as_of
        self._preventive_plan_repo.update(plan)
        self._session.commit()
        if due_instance is not None and self._scheduler.plan_uses_calendar_instances(plan):
            self._scheduler.sync_calendar_plan_instances(plan, as_of)
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
        sensor = (
            self._sensor_repo.get(plan_task.sensor_id_override)
            if plan_task.sensor_id_override
            else None
        )
        plan_task.last_generated_at = as_of
        plan_task.next_due_at = next_calendar_due_value(
            as_of, plan_task.calendar_frequency_unit_override, plan_task.calendar_frequency_value_override
        )
        plan_task.next_due_counter = next_sensor_due_counter(
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

    def _selected_plan_tasks(
        self,
        plan_id: str,
        candidate: MaintenancePreventiveDueCandidate,
    ) -> list[MaintenancePreventivePlanTask]:
        selected = set(candidate.selected_plan_task_ids)
        if not selected:
            return []
        rows = self._preventive_plan_task_repo.list_for_organization(
            self._active_organization().id, plan_id=plan_id
        )
        return [row for row in rows if row.id in selected]

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def _list_visible_active_plans(
        self,
        *,
        organization: Organization,
        site_id: str | None,
        plan_id: str | None,
    ) -> list[MaintenancePreventivePlan]:
        rows = self._preventive_plan_repo.list_for_organization(
            organization.id, active_only=True, site_id=site_id, status=MaintenancePlanStatus.ACTIVE
        )
        if plan_id is not None:
            rows = [row for row in rows if row.id == plan_id]
        return filter_scope_rows(
            rows, self._user_session,
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

    def _get_plan(self, plan_id: str, *, organization: Organization) -> MaintenancePreventivePlan:
        row = self._preventive_plan_repo.get(plan_id)
        if row is None or row.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance preventive plan not found in the active organization.",
                code="MAINTENANCE_PREVENTIVE_PLAN_NOT_FOUND",
            )
        return row

    def _active_organization(self) -> Organization:
        org = self._organization_repo.get_active()
        if org is None:
            raise NotFoundError("Active organization not found.", code="ORGANIZATION_NOT_FOUND")
        return org

    def _get_site(self, site_id: str, *, organization: Organization) -> Site:
        row = self._site_repo.get(site_id)
        if row is None or row.organization_id != organization.id:
            raise NotFoundError("Site not found in the active organization.", code="SITE_NOT_FOUND")
        return row

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.read", operation_label=operation_label)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.manage", operation_label=operation_label)

    def _require_scope_read(self, scope_id: str, *, operation_label: str) -> None:
        require_scope_permission(self._user_session, "maintenance", scope_id, "maintenance.read",
                                 operation_label=operation_label)

    def _require_scope_manage(self, scope_id: str, *, operation_label: str) -> None:
        require_scope_permission(self._user_session, "maintenance", scope_id, "maintenance.manage",
                                 operation_label=operation_label)


__all__ = ["MaintenancePreventiveGenerationService"]
