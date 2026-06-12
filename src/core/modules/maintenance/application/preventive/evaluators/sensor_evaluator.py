"""Sensor-based trigger evaluation for preventive plans."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from src.core.modules.maintenance.domain import (
    MaintenanceSensorDirection,
    MaintenanceSensorQualityState,
)
from src.core.modules.maintenance.application.preventive.models.candidates import MaintenanceTriggerEvaluation

if TYPE_CHECKING:
    from src.core.modules.maintenance.domain import MaintenanceSensor


def evaluate_sensor_trigger(
    *,
    sensor: "MaintenanceSensor | None",
    sensor_threshold: Decimal | None,
    sensor_direction: MaintenanceSensorDirection | None,
    last_generated_at: datetime | None,
    next_due_counter: Decimal | None,
) -> MaintenanceTriggerEvaluation:
    """Evaluate whether a sensor-value trigger is due, blocked, or pending."""
    if sensor is None or sensor_threshold is None or sensor_direction is None:
        return MaintenanceTriggerEvaluation(
            due=False,
            blocked=True,
            reason="Sensor trigger configuration is incomplete.",
        )
    if sensor.current_value is None or sensor.last_read_at is None:
        return MaintenanceTriggerEvaluation(
            due=False,
            blocked=True,
            reason="Linked preventive sensor has no usable reading.",
            sensor=sensor,
        )
    if sensor.last_quality_state != MaintenanceSensorQualityState.VALID:
        return MaintenanceTriggerEvaluation(
            due=False,
            blocked=True,
            reason="Linked preventive sensor is not in a valid quality state.",
            sensor=sensor,
        )
    if sensor_direction == MaintenanceSensorDirection.GREATER_OR_EQUAL:
        trigger_value = next_due_counter if next_due_counter is not None else sensor_threshold
        if sensor.current_value >= trigger_value:
            return MaintenanceTriggerEvaluation(
                due=True, blocked=False, reason="Sensor threshold reached.", sensor=sensor
            )
        return MaintenanceTriggerEvaluation(
            due=False, blocked=False, reason="Sensor threshold not yet reached.", sensor=sensor
        )
    if last_generated_at is not None and sensor.last_read_at <= last_generated_at:
        return MaintenanceTriggerEvaluation(
            due=False,
            blocked=False,
            reason="No newer qualifying sensor reading is available.",
            sensor=sensor,
        )
    if sensor_direction == MaintenanceSensorDirection.LESS_OR_EQUAL:
        due = sensor.current_value <= sensor_threshold
    else:
        due = sensor.current_value == sensor_threshold
    return MaintenanceTriggerEvaluation(
        due=due,
        blocked=False,
        reason="Sensor threshold reached." if due else "Sensor threshold not yet reached.",
        sensor=sensor,
    )


__all__ = ["evaluate_sensor_trigger"]
