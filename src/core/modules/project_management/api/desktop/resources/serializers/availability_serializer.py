from __future__ import annotations

from datetime import date

from src.core.modules.project_management.api.desktop.resources.models.availability import (
    ResourceAvailabilityDayDto,
    ResourceAvailabilityDto,
)


def _utilization_label(value) -> str:
    return "N/A" if value is None else f"{float(value):.1f}%"


def serialize_resource_availability_day(day) -> ResourceAvailabilityDayDto:
    return ResourceAvailabilityDayDto(
        work_date=day.work_date.isoformat(),
        date_label=day.work_date.strftime("%d %b"),
        base_capacity_hours=float(day.base_capacity_hours),
        effective_capacity_hours=float(day.effective_capacity_hours),
        planned_commitment_hours=float(day.planned_commitment_hours),
        remaining_capacity_hours=float(day.remaining_capacity_hours),
        utilization_percent=(
            None if day.utilization_percent is None else float(day.utilization_percent)
        ),
        utilization_label=_utilization_label(day.utilization_percent),
        overallocated=bool(day.overallocated),
        assignment_count=int(day.assignment_count),
    )


def serialize_resource_availability(
    resource_id: str,
    fact,
) -> ResourceAvailabilityDto:
    return ResourceAvailabilityDto(
        resource_id=resource_id,
        start_date=fact.start_date.isoformat(),
        end_date=fact.end_date.isoformat(),
        from_date_label=fact.start_date.strftime("%d %b %Y"),
        to_date_label=fact.end_date.strftime("%d %b %Y"),
        calendar_source_label=" -> ".join(fact.calendar_source_chain),
        capacity_percent=float(fact.capacity_percent),
        base_capacity_hours=float(fact.base_capacity_hours),
        effective_capacity_hours=float(fact.effective_capacity_hours),
        planned_commitment_hours=float(fact.planned_commitment_hours),
        allocated_planned_hours=float(fact.allocated_planned_hours),
        remaining_capacity_hours=float(fact.remaining_capacity_hours),
        utilization_percent=(
            None if fact.utilization_percent is None else float(fact.utilization_percent)
        ),
        utilization_label=_utilization_label(fact.utilization_percent),
        overallocated=bool(fact.overallocated),
        conflict_days=len(fact.conflict_dates),
        project_count=int(fact.project_count),
        assignment_count=int(fact.assignment_count),
        days=tuple(
            serialize_resource_availability_day(day)
            for day in fact.days
        ),
    )


__all__ = [
    "serialize_resource_availability",
    "serialize_resource_availability_day",
]
