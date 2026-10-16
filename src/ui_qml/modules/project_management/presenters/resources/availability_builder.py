from __future__ import annotations

from src.core.modules.project_management.api.desktop import (
    ProjectManagementResourcesDesktopApi,
)
from src.ui_qml.modules.project_management.view_models.resources import (
    ResourceAvailabilityDayViewModel,
    ResourceAvailabilityViewModel,
)


def build_resource_availability_state(
    desktop_api: ProjectManagementResourcesDesktopApi,
    resource_id: str,
    *,
    start_date: str,
    end_date: str,
) -> ResourceAvailabilityViewModel:
    dto = desktop_api.build_resource_availability(
        resource_id,
        start_date=start_date,
        end_date=end_date,
    )
    return ResourceAvailabilityViewModel(
        resource_id=dto.resource_id,
        start_date=dto.start_date.isoformat(),
        end_date=dto.end_date.isoformat(),
        from_date_label=dto.start_date.strftime("%d %b %Y"),
        to_date_label=dto.end_date.strftime("%d %b %Y"),
        calendar_source_label=" -> ".join(dto.calendar_source_chain),
        capacity_percent=float(dto.capacity_percent),
        base_capacity_hours=float(dto.base_capacity_hours),
        effective_capacity_hours=float(dto.effective_capacity_hours),
        planned_commitment_hours=float(dto.planned_commitment_hours),
        allocated_planned_hours=float(dto.allocated_planned_hours),
        remaining_capacity_hours=float(dto.remaining_capacity_hours),
        utilization_percent=None
        if dto.utilization_percent is None
        else float(dto.utilization_percent),
        utilization_label="N/A"
        if dto.utilization_percent is None
        else f"{dto.utilization_percent:.1f}%",
        overallocated=dto.overallocated,
        conflict_days=len(dto.conflict_dates),
        project_count=dto.project_count,
        assignment_count=dto.assignment_count,
        days=tuple(
            ResourceAvailabilityDayViewModel(
                work_date=day.work_date.isoformat(),
                date_label=day.work_date.strftime("%d %b"),
                base_capacity_hours=float(day.base_capacity_hours),
                effective_capacity_hours=float(day.effective_capacity_hours),
                planned_commitment_hours=float(day.planned_commitment_hours),
                remaining_capacity_hours=float(day.remaining_capacity_hours),
                utilization_percent=None
                if day.utilization_percent is None
                else float(day.utilization_percent),
                utilization_label="N/A"
                if day.utilization_percent is None
                else f"{day.utilization_percent:.1f}%",
                overallocated=day.overallocated,
                assignment_count=day.assignment_count,
            )
            for day in dto.days
        ),
    )


__all__ = ["build_resource_availability_state"]
