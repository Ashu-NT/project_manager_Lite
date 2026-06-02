"""Resource capacity calculator — derives capacity summary from calendar rules.

Capacity is NEVER stored. This service computes it on demand from resolved
calendar contexts. Caller injects assigned hours to get utilization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from src.core.platform.calendar.application.enterprise_calendar_resolver import (
    ResolvedCalendarContext,
)
from src.core.modules.project_management.application.resources.enterprise_resource_availability import (
    EnterpriseResourceAvailabilityService,
)


@dataclass
class ResourceCapacitySummary:
    resource_id: str
    start: date
    end: date
    base_hours: float
    available_hours: float
    assigned_hours: float
    remaining_hours: float
    capacity_percent: float
    utilization_percent: float
    working_days: int
    unavailable_days: int
    conflicts: list[str]
    source_chain: list[str]
    days: list[ResolvedCalendarContext] = field(default_factory=list)

    @property
    def is_overallocated(self) -> bool:
        return self.assigned_hours > self.available_hours


class ResourceCapacityCalculator:
    """
    Derives capacity summary for a resource over a date range.
    Does NOT persist capacity_percent.
    """

    def __init__(
        self,
        availability_service: EnterpriseResourceAvailabilityService,
    ) -> None:
        self._availability = availability_service

    def compute(
        self,
        resource_id: str,
        start: date,
        end: date,
        *,
        project_id: Optional[str] = None,
        site_id: Optional[str] = None,
        department_id: Optional[str] = None,
        assigned_hours_by_date: Optional[dict[date, float]] = None,
    ) -> ResourceCapacitySummary:
        days = self._availability.get_availability_range(
            resource_id,
            project_id=project_id,
            site_id=site_id,
            department_id=department_id,
            start=start,
            end=end,
            assigned_hours_by_date=assigned_hours_by_date,
        )

        base_total = sum(d.base_hours for d in days)
        available_total = sum(d.available_hours for d in days)
        assigned_total = sum(d.assigned_hours for d in days)
        remaining_total = max(0.0, available_total - assigned_total)
        working_days = sum(1 for d in days if d.base_hours > 0)
        unavailable_days = sum(1 for d in days if d.available_hours <= 0)

        capacity_pct = (
            round(available_total / base_total * 100, 2) if base_total > 0 else 0.0
        )
        utilization_pct = (
            round(assigned_total / available_total * 100, 2) if available_total > 0 else 0.0
        )

        conflicts = []
        for d in days:
            if d.assigned_hours > d.available_hours:
                conflicts.append(
                    f"{d.date}: assigned {d.assigned_hours:.1f}h > available {d.available_hours:.1f}h"
                )

        source_chain = (
            days[0].source_chain if days else []
        )

        return ResourceCapacitySummary(
            resource_id=resource_id,
            start=start,
            end=end,
            base_hours=round(base_total, 4),
            available_hours=round(available_total, 4),
            assigned_hours=round(assigned_total, 4),
            remaining_hours=round(remaining_total, 4),
            capacity_percent=capacity_pct,
            utilization_percent=utilization_pct,
            working_days=working_days,
            unavailable_days=unavailable_days,
            conflicts=conflicts,
            source_chain=source_chain,
            days=days,
        )


__all__ = ["ResourceCapacityCalculator", "ResourceCapacitySummary"]
