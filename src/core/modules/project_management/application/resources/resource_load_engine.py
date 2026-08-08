from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable


@dataclass(frozen=True, slots=True)
class ResourceLoadMetric:
    resource_id: str
    resource_name: str
    total_allocation_percent: float
    tasks_count: int
    capacity_percent: float
    utilization_percent: float


class ResourceLoadEngine:
    """Calculate peak concurrent load from already-acquired task facts."""

    @staticmethod
    def calculate(
        *,
        tasks: Iterable[object],
        assignments: Iterable[object],
        resources: Iterable[object],
        working_dates: frozenset[date],
    ) -> tuple[ResourceLoadMetric, ...]:
        task_rows = tuple(tasks)
        parent_ids = {
            str(parent_id)
            for task in task_rows
            if (parent_id := getattr(task, "parent_task_id", None))
        }
        tasks_by_id = {
            str(task.id): task
            for task in task_rows
            if str(task.id) not in parent_ids
        }
        resources_by_id = {str(resource.id): resource for resource in resources}
        counts: dict[str, int] = {}
        unscheduled: dict[str, float] = {}
        daily: dict[str, dict[date, float]] = {}

        for assignment in assignments:
            task = tasks_by_id.get(str(assignment.task_id))
            if task is None:
                continue
            resource_id = str(assignment.resource_id)
            allocation = float(assignment.allocation_percent or 0.0)
            counts[resource_id] = counts.get(resource_id, 0) + 1
            start = getattr(task, "start_date", None)
            end = getattr(task, "end_date", None)
            if allocation > 0.0 and start and end:
                if end < start:
                    start, end = end, start
                bucket = daily.setdefault(resource_id, {})
                for working_date in working_dates:
                    if start <= working_date <= end:
                        bucket[working_date] = bucket.get(working_date, 0.0) + allocation
            elif allocation > 0.0:
                unscheduled[resource_id] = unscheduled.get(resource_id, 0.0) + allocation

        metrics: list[ResourceLoadMetric] = []
        for resource_id, tasks_count in counts.items():
            peak = max(daily.get(resource_id, {}).values(), default=0.0)
            total = float(peak + unscheduled.get(resource_id, 0.0))
            resource = resources_by_id.get(resource_id)
            name = str(getattr(resource, "name", "<unknown>") or "<unknown>")
            capacity = float(getattr(resource, "capacity_percent", 100.0) or 100.0)
            if capacity <= 0.0:
                capacity = 100.0
            metrics.append(
                ResourceLoadMetric(
                    resource_id=resource_id,
                    resource_name=name,
                    total_allocation_percent=total,
                    tasks_count=tasks_count,
                    capacity_percent=capacity,
                    utilization_percent=(total / capacity) * 100.0,
                )
            )
        metrics.sort(
            key=lambda row: (row.utilization_percent, row.total_allocation_percent),
            reverse=True,
        )
        return tuple(metrics)


__all__ = ["ResourceLoadEngine", "ResourceLoadMetric"]
