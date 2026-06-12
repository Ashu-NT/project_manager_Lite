"""Preventive schedule forecast — planner state computation."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from src.core.modules.maintenance.domain import MaintenancePreventiveInstanceStatus
from src.core.modules.maintenance.application.preventive.utils.date_utils import (
    lead_window_starts_at,
    resolve_as_of,
)

if TYPE_CHECKING:
    from src.core.modules.maintenance.domain import (
        MaintenancePreventivePlan,
        MaintenancePreventivePlanInstance,
    )


def forecast_planner_state(
    plan: "MaintenancePreventivePlan",
    row: "MaintenancePreventivePlanInstance",
    as_of: datetime,
) -> str:
    """
    Derive the display state for a scheduled instance in a forecast view.

    States: COMPLETED | GENERATED | CANCELLED | DUE | READY_WINDOW | UPCOMING
    """
    if row.status == MaintenancePreventiveInstanceStatus.COMPLETED:
        return "COMPLETED"
    if row.status == MaintenancePreventiveInstanceStatus.GENERATED:
        return "GENERATED"
    if row.status == MaintenancePreventiveInstanceStatus.CANCELLED:
        return "CANCELLED"
    due_at = resolve_as_of(row.due_at)
    window_opens_at = lead_window_starts_at(plan, due_at)
    if as_of >= due_at:
        return "DUE"
    if as_of >= window_opens_at:
        return "READY_WINDOW"
    return "UPCOMING"


__all__ = ["forecast_planner_state"]
