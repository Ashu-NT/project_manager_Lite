from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone as dt_timezone

from src.core.platform.common.ids import generate_id


@dataclass
class Site:
    id: str
    organization_id: str
    site_code: str
    name: str
    description: str = ""
    country: str = ""
    region: str = ""
    city: str = ""
    address_line_1: str = ""
    address_line_2: str = ""
    postal_code: str = ""
    timezone: str = ""
    currency_code: str = ""
    site_type: str = ""
    status: str = "ACTIVE"
    default_calendar_id: str = ""
    default_language: str = ""
    is_active: bool = True
    opened_at: datetime | None = None
    closed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    notes: str = ""
    version: int = 1

    @staticmethod
    def create(
        organization_id: str,
        site_code: str,
        name: str,
        *,
        description: str = "",
        country: str = "",
        region: str = "",
        city: str = "",
        address_line_1: str = "",
        address_line_2: str = "",
        postal_code: str = "",
        timezone: str = "",
        currency_code: str = "",
        site_type: str = "",
        status: str = "ACTIVE",
        default_calendar_id: str = "",
        default_language: str = "",
        is_active: bool = True,
        opened_at: datetime | None = None,
        closed_at: datetime | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        notes: str = "",
    ) -> "Site":
        now = datetime.now(dt_timezone.utc)
        return Site(
            id=generate_id(),
            organization_id=organization_id,
            site_code=site_code,
            name=name,
            description=description,
            country=country,
            region=region,
            city=city,
            address_line_1=address_line_1,
            address_line_2=address_line_2,
            postal_code=postal_code,
            timezone=timezone,
            currency_code=currency_code,
            site_type=site_type,
            status=status,
            default_calendar_id=default_calendar_id,
            default_language=default_language,
            is_active=is_active,
            opened_at=opened_at,
            closed_at=closed_at,
            created_at=created_at or now,
            updated_at=updated_at or now,
            notes=notes,
            version=1,
        )

    @property
    def display_name(self) -> str:
        return self.name

    @display_name.setter
    def display_name(self, value: str) -> None:
        self.name = value


__all__ = ["Site"]
