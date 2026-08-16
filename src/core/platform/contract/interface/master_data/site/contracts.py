from __future__ import annotations

from typing import Protocol


class LocationReference(Protocol):
    id: str
    organization_id: str
    site_id: str
    location_code: str
    name: str
    is_active: bool


__all__ = ["LocationReference"]
