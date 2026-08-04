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


@dataclass(frozen=True)
class SiteCreateCommand:
    site_code: str
    name: str
    description: str = ""
    country: str = ""
    region: str = ""
    city: str = ""
    address_line_1: str = ""
    address_line_2: str = ""
    postal_code: str = ""
    timezone_name: str = ""
    currency_code: str = ""
    site_type: str = ""
    status: str = ""
    default_calendar_id: str = ""
    default_language: str = ""
    is_active: bool = True
    notes: str = ""


@dataclass(frozen=True)
class SiteUpdateCommand:
    site_id: str
    site_code: str | None = None
    name: str | None = None
    description: str | None = None
    country: str | None = None
    region: str | None = None
    city: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    postal_code: str | None = None
    timezone_name: str | None = None
    currency_code: str | None = None
    site_type: str | None = None
    status: str | None = None
    default_calendar_id: str | None = None
    default_language: str | None = None
    is_active: bool | None = None
    notes: str | None = None
    expected_version: int | None = None
