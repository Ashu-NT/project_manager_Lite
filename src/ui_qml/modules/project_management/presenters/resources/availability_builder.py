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
        start_date=dto.start_date,
        end_date=dto.end_date,
        from_date_label=dto.from_date_label,
        to_date_label=dto.to_date_label,
        calendar_source_label=dto.calendar_source_label,
        capacity_percent=dto.capacity_percent,
        base_capacity_hours=dto.base_capacity_hours,
        effective_capacity_hours=dto.effective_capacity_hours,
        planned_commitment_hours=dto.planned_commitment_hours,
        allocated_planned_hours=dto.allocated_planned_hours,
        remaining_capacity_hours=dto.remaining_capacity_hours,
        utilization_percent=dto.utilization_percent,
        utilization_label=dto.utilization_label,
        overallocated=dto.overallocated,
        conflict_days=dto.conflict_days,
        project_count=dto.project_count,
        assignment_count=dto.assignment_count,
        days=tuple(
            ResourceAvailabilityDayViewModel(
                work_date=day.work_date,
                date_label=day.date_label,
                base_capacity_hours=day.base_capacity_hours,
                effective_capacity_hours=day.effective_capacity_hours,
                planned_commitment_hours=day.planned_commitment_hours,
                remaining_capacity_hours=day.remaining_capacity_hours,
                utilization_percent=day.utilization_percent,
                utilization_label=day.utilization_label,
                overallocated=day.overallocated,
                assignment_count=day.assignment_count,
            )
            for day in dto.days
        ),
    )


__all__ = ["build_resource_availability_state"]
