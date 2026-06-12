from dataclasses import dataclass


@dataclass(frozen=True)
class SchedulingResourceLoadDto:
    resource_id: str
    resource_name: str
    total_allocation_percent: float
    total_allocation_label: str
    capacity_percent: float
    capacity_label: str
    utilization_percent: float
    utilization_label: str
    tasks_count: int
    status_label: str


__all__ = ["SchedulingResourceLoadDto"]
