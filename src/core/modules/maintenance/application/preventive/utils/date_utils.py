"""Date arithmetic utilities shared across preventive plan services.

These functions were previously duplicated between the generation service and plan
service. They are now the single source of truth for all preventive date math.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from src.core.modules.maintenance.domain import (
    MaintenanceCalendarFrequencyUnit,
    MaintenanceGenerationLeadUnit,
    MaintenanceSensorDirection,
)

if TYPE_CHECKING:
    from src.core.modules.maintenance.domain import MaintenancePreventivePlan, MaintenanceSensor


def resolve_as_of(as_of: datetime | None) -> datetime:
    """Normalise an optional datetime to UTC-aware. Returns now() if None."""
    if as_of is None:
        return datetime.now(timezone.utc)
    if as_of.tzinfo is None:
        return as_of.replace(tzinfo=timezone.utc)
    return as_of.astimezone(timezone.utc)


def add_months(anchor: datetime, months: int) -> datetime:
    """Add a signed number of months to a datetime, clamping to month-end."""
    total_month = anchor.month - 1 + months
    year = anchor.year + total_month // 12
    month = total_month % 12 + 1
    day = min(anchor.day, monthrange(year, month)[1])
    return anchor.replace(year=year, month=month, day=day)


def advance_calendar_due(
    anchor: datetime,
    unit: MaintenanceCalendarFrequencyUnit,
    value: int,
) -> datetime:
    """Advance *anchor* by one recurrence period defined by (unit, value)."""
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
    return add_months(anchor, months)


def lead_window_starts_at(
    plan: "MaintenancePreventivePlan",
    due_at: datetime,
) -> datetime:
    """Return the datetime when the lead generation window opens for a scheduled due date."""
    lead_value = max(int(getattr(plan, "generation_lead_value", 0) or 0), 0)
    if lead_value == 0:
        return due_at
    lead_unit = getattr(plan, "generation_lead_unit", MaintenanceGenerationLeadUnit.DAYS)
    if lead_unit == MaintenanceGenerationLeadUnit.DAYS:
        return due_at - timedelta(days=lead_value)
    if lead_unit == MaintenanceGenerationLeadUnit.WEEKS:
        return due_at - timedelta(weeks=lead_value)
    return add_months(due_at, -lead_value)


def next_calendar_due_value(
    as_of: datetime,
    unit: MaintenanceCalendarFrequencyUnit | None,
    value: int | None,
) -> datetime | None:
    """Compute the next calendar due date after generation, or None if not applicable."""
    if unit is None or value in (None, 0):
        return None
    return advance_calendar_due(as_of, unit, value)


def next_sensor_due_counter(
    *,
    sensor: "MaintenanceSensor | None",
    threshold: Decimal | None,
    direction: MaintenanceSensorDirection | None,
    current_due_counter: Decimal | None,
) -> Decimal | None:
    """Compute the next sensor counter threshold after generation."""
    if sensor is None or sensor.current_value is None or threshold is None or direction is None:
        return None
    if direction == MaintenanceSensorDirection.GREATER_OR_EQUAL:
        base_value = current_due_counter if current_due_counter is not None else threshold
        while sensor.current_value >= base_value:
            base_value += threshold
        return base_value
    return current_due_counter


__all__ = [
    "add_months",
    "advance_calendar_due",
    "lead_window_starts_at",
    "next_calendar_due_value",
    "next_sensor_due_counter",
    "resolve_as_of",
]
