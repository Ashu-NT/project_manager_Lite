"""Composite trigger evaluation — dispatches to calendar, sensor, or hybrid."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from src.core.modules.maintenance.domain import MaintenanceTriggerMode
from src.core.modules.maintenance.application.preventive.models.candidates import MaintenanceTriggerEvaluation
from src.core.modules.maintenance.application.preventive.evaluators.calendar_evaluator import (
    evaluate_calendar_trigger,
)
from src.core.modules.maintenance.application.preventive.evaluators.sensor_evaluator import (
    evaluate_sensor_trigger,
)

if TYPE_CHECKING:
    from src.core.modules.maintenance.domain import (
        MaintenanceCalendarFrequencyUnit,
        MaintenancePreventivePlan,
        MaintenancePreventivePlanTask,
        MaintenanceSensor,
        MaintenanceSensorDirection,
    )


def evaluate_trigger_state(
    *,
    trigger_mode: MaintenanceTriggerMode,
    calendar_frequency_unit: "MaintenanceCalendarFrequencyUnit | None",
    calendar_frequency_value: int | None,
    sensor: "MaintenanceSensor | None",
    sensor_threshold: Decimal | None,
    sensor_direction: "MaintenanceSensorDirection | None",
    last_generated_at: datetime | None,
    next_due_at: datetime | None,
    next_due_counter: Decimal | None,
    as_of: datetime,
) -> MaintenanceTriggerEvaluation:
    """Route trigger evaluation to the appropriate strategy (calendar/sensor/hybrid)."""
    if trigger_mode == MaintenanceTriggerMode.CALENDAR:
        return evaluate_calendar_trigger(
            calendar_frequency_unit=calendar_frequency_unit,
            calendar_frequency_value=calendar_frequency_value,
            last_generated_at=last_generated_at,
            next_due_at=next_due_at,
            as_of=as_of,
        )
    sensor_eval = evaluate_sensor_trigger(
        sensor=sensor,
        sensor_threshold=sensor_threshold,
        sensor_direction=sensor_direction,
        last_generated_at=last_generated_at,
        next_due_counter=next_due_counter,
    )
    if trigger_mode == MaintenanceTriggerMode.SENSOR:
        return sensor_eval

    # HYBRID: sensor blocked → blocked; sensor due → due; calendar due → due
    if sensor_eval.blocked:
        return MaintenanceTriggerEvaluation(
            due=False,
            blocked=True,
            reason="Hybrid trigger is blocked because the linked sensor state is not usable.",
            sensor=sensor_eval.sensor,
        )
    if sensor_eval.due:
        return MaintenanceTriggerEvaluation(
            due=True,
            blocked=False,
            reason="Hybrid preventive trigger is due from sensor state.",
            sensor=sensor_eval.sensor,
        )
    calendar_eval = evaluate_calendar_trigger(
        calendar_frequency_unit=calendar_frequency_unit,
        calendar_frequency_value=calendar_frequency_value,
        last_generated_at=last_generated_at,
        next_due_at=next_due_at,
        as_of=as_of,
    )
    if calendar_eval.due:
        return MaintenanceTriggerEvaluation(
            due=True,
            blocked=False,
            reason="Hybrid preventive trigger is due from calendar cadence.",
            sensor=sensor_eval.sensor,
        )
    return MaintenanceTriggerEvaluation(
        due=False,
        blocked=False,
        reason="Hybrid preventive trigger is not due.",
        sensor=sensor_eval.sensor,
    )


def evaluate_plan_trigger(
    plan: "MaintenancePreventivePlan",
    *,
    sensor: "MaintenanceSensor | None",
    as_of: datetime,
) -> MaintenanceTriggerEvaluation:
    """Evaluate the plan-level trigger (not a task-level override)."""
    return evaluate_trigger_state(
        trigger_mode=plan.trigger_mode,
        calendar_frequency_unit=plan.calendar_frequency_unit,
        calendar_frequency_value=plan.calendar_frequency_value,
        sensor=sensor,
        sensor_threshold=plan.sensor_threshold,
        sensor_direction=plan.sensor_direction,
        last_generated_at=plan.last_generated_at,
        next_due_at=plan.next_due_at,
        next_due_counter=plan.next_due_counter,
        as_of=as_of,
    )


def evaluate_plan_task_trigger(
    plan_task: "MaintenancePreventivePlanTask",
    *,
    sensor: "MaintenanceSensor | None",
    as_of: datetime,
) -> MaintenanceTriggerEvaluation:
    """Evaluate a task-level trigger override."""
    return evaluate_trigger_state(
        trigger_mode=plan_task.trigger_mode_override,
        calendar_frequency_unit=plan_task.calendar_frequency_unit_override,
        calendar_frequency_value=plan_task.calendar_frequency_value_override,
        sensor=sensor,
        sensor_threshold=plan_task.sensor_threshold_override,
        sensor_direction=plan_task.sensor_direction_override,
        last_generated_at=plan_task.last_generated_at,
        next_due_at=plan_task.next_due_at,
        next_due_counter=plan_task.next_due_counter,
        as_of=as_of,
    )


__all__ = ["evaluate_plan_task_trigger", "evaluate_plan_trigger", "evaluate_trigger_state"]
