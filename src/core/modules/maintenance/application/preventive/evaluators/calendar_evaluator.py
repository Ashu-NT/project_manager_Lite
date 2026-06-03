"""Calendar-based trigger evaluation for preventive plans."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from src.core.modules.maintenance.application.preventive.models.candidates import MaintenanceTriggerEvaluation
from src.core.modules.maintenance.application.preventive.utils.date_utils import (
    advance_calendar_due,
    lead_window_starts_at,
    resolve_as_of,
)

if TYPE_CHECKING:
    from src.core.modules.maintenance.domain import (
        MaintenanceCalendarFrequencyUnit,
        MaintenancePreventivePlan,
        MaintenancePreventivePlanInstance,
    )


def evaluate_calendar_trigger(
    *,
    calendar_frequency_unit: "MaintenanceCalendarFrequencyUnit | None",
    calendar_frequency_value: int | None,
    last_generated_at: datetime | None,
    next_due_at: datetime | None,
    as_of: datetime,
) -> MaintenanceTriggerEvaluation:
    """Evaluate whether a calendar-cadence trigger is due."""
    if calendar_frequency_unit is None or calendar_frequency_value in (None, 0):
        return MaintenanceTriggerEvaluation(
            due=False,
            blocked=True,
            reason="Calendar trigger configuration is incomplete.",
        )
    effective_next_due = next_due_at
    if effective_next_due is not None:
        effective_next_due = resolve_as_of(effective_next_due)
    if effective_next_due is None and last_generated_at is not None:
        effective_next_due = advance_calendar_due(
            resolve_as_of(last_generated_at),
            calendar_frequency_unit,
            calendar_frequency_value,
        )
    if effective_next_due is None:
        return MaintenanceTriggerEvaluation(
            due=True,
            blocked=False,
            reason="Preventive plan is due because no previous generation exists.",
        )
    if as_of >= effective_next_due:
        return MaintenanceTriggerEvaluation(
            due=True,
            blocked=False,
            reason="Preventive plan reached its calendar due date.",
        )
    return MaintenanceTriggerEvaluation(
        due=False,
        blocked=False,
        reason="Preventive plan has not reached its calendar due date.",
    )


def evaluate_calendar_instance_window(
    *,
    plan: "MaintenancePreventivePlan",
    instances: "list[MaintenancePreventivePlanInstance]",
    as_of: datetime,
) -> MaintenanceTriggerEvaluation:
    """Evaluate whether the next scheduled instance is within its lead generation window."""
    if not instances:
        return MaintenanceTriggerEvaluation(
            due=False,
            blocked=True,
            reason="Preventive plan has no planned schedule instances to generate from.",
        )
    next_instance = instances[0]
    due_at = resolve_as_of(next_instance.due_at)
    window_opens_at = lead_window_starts_at(plan, due_at)

    if as_of >= due_at:
        return MaintenanceTriggerEvaluation(
            due=True,
            blocked=False,
            reason=f"Preventive plan reached its scheduled due date on {due_at.isoformat()}.",
        )
    if as_of >= window_opens_at:
        if window_opens_at == due_at:
            return MaintenanceTriggerEvaluation(
                due=True,
                blocked=False,
                reason="Preventive plan reached its generation window on the due date.",
            )
        return MaintenanceTriggerEvaluation(
            due=True,
            blocked=False,
            reason=(
                "Preventive plan entered its lead generation window "
                f"on {window_opens_at.isoformat()} for scheduled due date {due_at.isoformat()}."
            ),
        )
    return MaintenanceTriggerEvaluation(
        due=False,
        blocked=False,
        reason=(
            f"Preventive plan is scheduled for {due_at.isoformat()}; "
            f"generation window opens at {window_opens_at.isoformat()}."
        ),
    )


__all__ = ["evaluate_calendar_instance_window", "evaluate_calendar_trigger"]
