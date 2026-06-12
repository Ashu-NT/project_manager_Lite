from __future__ import annotations

from datetime import date

from src.core.modules.project_management.api.desktop.resources.models.availability import (
    ResourceAvailabilityDayDto,
    ResourceAvailabilityDto,
)


def serialize_resource_availability_day(day) -> ResourceAvailabilityDayDto:
    return ResourceAvailabilityDayDto(
        date_label=day.check_date.strftime("%d %b"),
        allocation_percent=float(day.total_allocation_percent or 0.0),
        allocation_label=f"{day.total_allocation_percent:.0f}%",
        overloaded=bool(day.overloaded),
    )


def serialize_resource_availability(
    resource_id: str,
    window,
    *,
    from_date: date,
    to_date: date,
) -> ResourceAvailabilityDto:
    all_days = getattr(window, "daily_loads", []) or []
    return ResourceAvailabilityDto(
        resource_id=resource_id,
        peak_load_percent=float(window.peak_load_percent or 0.0),
        average_load_percent=float(window.average_load_percent or 0.0),
        overloaded_days=int(window.overloaded_days or 0),
        available_days=int(window.available_days or 0),
        is_available=bool(window.is_available),
        from_date_label=from_date.strftime("%d %b %Y"),
        to_date_label=to_date.strftime("%d %b %Y"),
        days=tuple(
            serialize_resource_availability_day(day)
            for day in all_days[:90]
        ),
    )


__all__ = [
    "serialize_resource_availability",
    "serialize_resource_availability_day",
]
