from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SiteDto:
    id: str
    organization_id: str
    site_code: str
    name: str
    description: str
    country: str
    region: str
    city: str
    address_line_1: str
    address_line_2: str
    postal_code: str
    timezone: str
    currency_code: str
    site_type: str
    status: str
    default_calendar_id: str
    default_language: str
    is_active: bool
    notes: str
    version: int
    opened_at: datetime | None = None
    closed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class SitePageDto:
    items: tuple[SiteDto, ...] = ()
    total: int = 0
    filtered_total: int = 0
    page: int = 1
    page_size: int = 25




