from __future__ import annotations

from src.core.modules.project_management.api.desktop.tasks.models.reservation import (
    TaskMaterialDemandSummary,
    TaskReservationDesktopDto,
)


def build_material_demand_summary(
    task_id: str,
    reservations: tuple[TaskReservationDesktopDto, ...],
) -> TaskMaterialDemandSummary:
    active_statuses = {"ACTIVE", "PARTIALLY_ISSUED"}
    fulfilled_statuses = {"FULLY_ISSUED"}
    closed_statuses = {"RELEASED", "CANCELLED"}
    return TaskMaterialDemandSummary(
        task_id=task_id,
        total_reserved=len(reservations),
        active_count=sum(1 for r in reservations if r.status in active_statuses),
        fulfilled_count=sum(1 for r in reservations if r.status in fulfilled_statuses),
        cancelled_count=sum(1 for r in reservations if r.status in closed_statuses),
    )


__all__ = ["build_material_demand_summary"]
