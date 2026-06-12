from __future__ import annotations

from src.core.modules.project_management.api.desktop import (
    ProjectManagementResourcesDesktopApi,
)
from src.ui_qml.modules.project_management.view_models.resources import (
    ResourceAvailabilityDayViewModel,
    ResourceAvailabilityViewModel,
)


def build_availability_view_model(
    desktop_api: ProjectManagementResourcesDesktopApi,
    resource_id: str,
) -> ResourceAvailabilityViewModel:
    if not resource_id:
        return ResourceAvailabilityViewModel()
    dto = desktop_api.build_resource_availability(resource_id)
    if dto is None:
        return ResourceAvailabilityViewModel(resource_id=resource_id)
    return ResourceAvailabilityViewModel(
        resource_id=dto.resource_id,
        peak_load_percent=dto.peak_load_percent,
        average_load_percent=dto.average_load_percent,
        overloaded_days=dto.overloaded_days,
        available_days=dto.available_days,
        is_available=dto.is_available,
        from_date_label=dto.from_date_label,
        to_date_label=dto.to_date_label,
        days=tuple(
            ResourceAvailabilityDayViewModel(
                date_label=d.date_label,
                allocation_percent=d.allocation_percent,
                allocation_label=d.allocation_label,
                overloaded=d.overloaded,
            )
            for d in dto.days
        ),
    )
