"""Resource load serializer."""

from src.core.modules.project_management.api.desktop.scheduling.models.resources import SchedulingResourceLoadDto
from src.core.modules.project_management.api.desktop.scheduling.formatters.status_formatter import resource_load_status_label


def serialize_resource_load_row(row) -> SchedulingResourceLoadDto:
    utilization = float(getattr(row, "utilization_percent", row.total_allocation_percent) or 0.0)
    capacity = float(getattr(row, "capacity_percent", 100.0) or 100.0)
    allocation = float(row.total_allocation_percent or 0.0)
    return SchedulingResourceLoadDto(
        resource_id=row.resource_id,
        resource_name=row.resource_name,
        total_allocation_percent=allocation,
        total_allocation_label=f"{allocation:.1f}%",
        capacity_percent=capacity,
        capacity_label=f"{capacity:.1f}%",
        utilization_percent=utilization,
        utilization_label=f"{utilization:.1f}%",
        tasks_count=int(getattr(row, "tasks_count", 0) or 0),
        status_label=resource_load_status_label(utilization),
    )


__all__ = ["serialize_resource_load_row"]
