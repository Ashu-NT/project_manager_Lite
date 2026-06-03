"""Manages preventive plan schedule instances — syncing, building due dates, selecting."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from src.core.modules.maintenance.domain import (
    MaintenancePreventiveInstanceStatus,
    MaintenancePreventivePlan,
    MaintenancePreventivePlanInstance,
    MaintenanceTriggerMode,
)
from src.core.modules.maintenance.contracts.repositories import (
    MaintenanceBlackoutWindowRepository,
    MaintenancePreventivePlanInstanceRepository,
    MaintenancePreventivePlanRepository,
)
from src.core.modules.maintenance.application.preventive.utils.date_utils import (
    advance_calendar_due,
    lead_window_starts_at,
    resolve_as_of,
)


class PreventiveInstanceScheduler:
    """
    Manages the lifecycle of preventive plan schedule instances.

    Syncs planned instances against the computed recurrence horizon,
    selects the due instance for generation, and builds the planned due dates.
    """

    def __init__(
        self,
        session: Session,
        *,
        instance_repo: MaintenancePreventivePlanInstanceRepository,
        plan_repo: MaintenancePreventivePlanRepository,
        blackout_window_repo: MaintenanceBlackoutWindowRepository | None = None,
    ) -> None:
        self._session = session
        self._instance_repo = instance_repo
        self._plan_repo = plan_repo
        self._blackout_window_repo = blackout_window_repo

    def plan_uses_calendar_instances(self, plan: MaintenancePreventivePlan) -> bool:
        """Return True when the plan uses a scheduled instance model (calendar trigger with frequency)."""
        return (
            plan.trigger_mode == MaintenanceTriggerMode.CALENDAR
            and plan.calendar_frequency_unit is not None
            and plan.calendar_frequency_value not in (None, 0)
        )

    def sync_calendar_plan_instances(
        self,
        plan: MaintenancePreventivePlan,
        as_of: datetime,
    ) -> list[MaintenancePreventivePlanInstance]:
        """
        Synchronise the set of PLANNED instances against the desired horizon.

        Creates missing instances, removes orphaned planned instances, and
        updates `plan.next_due_at` to match the nearest planned instance.
        """
        if not self.plan_uses_calendar_instances(plan):
            return self._instance_repo.list_for_organization(
                plan.organization_id,
                plan_id=plan.id,
            )
        rows = self._instance_repo.list_for_organization(plan.organization_id, plan_id=plan.id)
        planned_by_due = {
            resolve_as_of(row.due_at): row
            for row in rows
            if row.status == MaintenancePreventiveInstanceStatus.PLANNED
        }
        desired_due_dates = self.build_planned_due_dates(plan, as_of)
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
            self._instance_repo.add(instance)
            desired_instances.append(instance)
            changed = True

        for orphan in planned_by_due.values():
            self._instance_repo.delete(orphan.id)
            changed = True

        next_due_at = desired_instances[0].due_at if desired_instances else None
        if plan.next_due_at != next_due_at:
            plan.next_due_at = next_due_at
            plan.updated_at = as_of
            self._plan_repo.update(plan)
            changed = True

        if changed:
            self._session.commit()

        return self._normalize(
            self._instance_repo.list_for_organization(plan.organization_id, plan_id=plan.id)
        )

    def build_planned_due_dates(
        self,
        plan: MaintenancePreventivePlan,
        as_of: datetime,
    ) -> list[datetime]:
        """Build the ordered list of desired due dates for the planning horizon."""
        if plan.calendar_frequency_unit is None or plan.calendar_frequency_value in (None, 0):
            return []

        start_due = resolve_as_of(plan.next_due_at) if plan.next_due_at is not None else None
        if start_due is None:
            start_due = advance_calendar_due(
                as_of,
                plan.calendar_frequency_unit,
                plan.calendar_frequency_value,
            )

        blackout_windows = (
            self._blackout_window_repo.list_for_plan(plan.organization_id, plan.id, active_only=True)
            if self._blackout_window_repo is not None
            else []
        )

        planned_due_dates: list[datetime] = []
        current_due = start_due
        generated = 0
        horizon = max(plan.generation_horizon_count, 1)
        max_iter = horizon * 4  # guard against infinite loop
        iterations = 0

        while generated < horizon and iterations < max_iter:
            iterations += 1
            due_date = current_due.date() if hasattr(current_due, "date") else current_due
            if not any(w.covers(due_date) for w in blackout_windows):
                planned_due_dates.append(current_due)
                generated += 1
            current_due = advance_calendar_due(
                current_due,
                plan.calendar_frequency_unit,
                plan.calendar_frequency_value,
            )

        return planned_due_dates

    def select_due_instance(
        self,
        plan: MaintenancePreventivePlan,
        as_of: datetime,
    ) -> MaintenancePreventivePlanInstance | None:
        """Return the earliest PLANNED instance whose lead window has opened, or None."""
        if not self.plan_uses_calendar_instances(plan):
            return None
        for row in self._instance_repo.list_for_organization(
            plan.organization_id,
            plan_id=plan.id,
            status=MaintenancePreventiveInstanceStatus.PLANNED.value,
        ):
            if as_of >= lead_window_starts_at(plan, resolve_as_of(row.due_at)):
                return row
        return None

    def list_instances(
        self,
        plan: MaintenancePreventivePlan,
        *,
        status: str | None = None,
    ) -> list[MaintenancePreventivePlanInstance]:
        """Return all instances for the plan, optionally filtered by status."""
        return self._normalize(
            self._instance_repo.list_for_organization(
                plan.organization_id, plan_id=plan.id, status=status
            )
        )

    def _normalize(
        self,
        rows: list[MaintenancePreventivePlanInstance],
    ) -> list[MaintenancePreventivePlanInstance]:
        for row in rows:
            row.due_at = resolve_as_of(row.due_at)
            if row.generated_at is not None:
                row.generated_at = resolve_as_of(row.generated_at)
            if row.completed_at is not None:
                row.completed_at = resolve_as_of(row.completed_at)
        return rows


__all__ = ["PreventiveInstanceScheduler"]
