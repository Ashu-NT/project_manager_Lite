from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceAvailabilityDayDto:
    date_label: str
    allocation_percent: float
    allocation_label: str
    overloaded: bool


@dataclass(frozen=True)
class ResourceAvailabilityDto:
    resource_id: str
    peak_load_percent: float
    average_load_percent: float
    overloaded_days: int
    available_days: int
    is_available: bool
    from_date_label: str
    to_date_label: str
    days: tuple[ResourceAvailabilityDayDto, ...]


__all__ = ["ResourceAvailabilityDayDto", "ResourceAvailabilityDto"]
