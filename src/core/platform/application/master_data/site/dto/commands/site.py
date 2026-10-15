from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


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
    default_calendar_id: str = ""
    default_language: str = ""
    notes: str = ""
    opened_at: datetime | None = None
    closed_at: datetime | None = None


@dataclass(frozen=True)
class SiteUpdateCommand:
    """Pure profile update -- lifecycle (status/is_active) is never accepted
    here; use PlatformSiteDesktopApi.activate_site/deactivate_site/
    archive_site instead, each with its own guarded transition."""

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
    default_calendar_id: str | None = None
    default_language: str | None = None
    notes: str | None = None
    opened_at: datetime | None = None
    closed_at: datetime | None = None
    expected_version: int | None = None
