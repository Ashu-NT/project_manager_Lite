from __future__ import annotations

from zoneinfo import available_timezones, ZoneInfo 

# IANA time zone database identifiers (sourced from python-dateutil's bundled
# tzdata, since zoneinfo.available_timezones() returns nothing on a Windows
# host without a separate tzdata package installed). Static reference data
# only -- no lifecycle, no persistence, no per-tenant customization. Backs
# the timezone picker on Organization; timezone_name itself is stored as a
# plain string and is never validated against this list (an unrecognized/
# future identifier must not block saving an organization).

IANA_TIMEZONES = frozenset(available_timezones())

TIMEZONE_OPTIONS: tuple[tuple[str, str], ...] = tuple(
    (name, name) for name in sorted(IANA_TIMEZONES)
)


def is_known_timezone(name: str) -> bool:
    """Whether name is a recognized IANA identifier -- callers should still
    accept and display an unrecognized value rather than reject it."""
    return str(name or "").strip() in IANA_TIMEZONES


__all__ = [
    "IANA_TIMEZONES",
    "TIMEZONE_OPTIONS",
    "is_known_timezone",
]
