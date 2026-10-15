"""Calendar calendars inputs and results."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class CalendarCreateCommand:
    code: str
    name: str
    calendar_type: str
    timezone: str = "UTC"
    description: str = ""
    base_calendar_id: str = ""
    scope_type: str | None = None
    scope_id: str | None = None
    locale: str = ""
    is_default: bool = False
    effective_from: date | str | None = None
    effective_to: date | str | None = None
    priority: int = 0


@dataclass(frozen=True)
class CalendarUpdateCommand:
    # No is_default field -- changing the organization's default calendar is
    # an explicit, atomic operation (set_organization_default_calendar),
    # never part of this generic profile update.
    calendar_id: str
    name: str = ""
    description: str = ""
    timezone: str = ""
    locale: str = ""
    is_active: bool | None = None
    effective_from: date | str | None = None
    effective_to: date | str | None = None
    priority: int | None = None
