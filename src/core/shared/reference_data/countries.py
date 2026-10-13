from __future__ import annotations

import pycountry

# ISO 3166-1 alpha-2 codes and English short names. Static reference data
# only -- no lifecycle, no persistence, no per-tenant customization. Backs
# the country picker on Organization's registered address; country_code
# itself is stored as a plain string and is never validated against this
# list (an unrecognized/future code must not block saving an organization).

COUNTRY_OPTIONS: tuple[tuple[str, str], ...] = tuple(
    sorted(
        (
            (country.alpha_2, country.name) 
            for country in pycountry.countries
        ), 
        key=lambda pair: pair[1])
)


def country_name_for_code(code: str) -> str:
    """Display name for an ISO 3166-1 alpha-2 code, or "" if blank/unrecognized
    -- callers fall back to showing the raw code so an unrecognized value is
    never silently hidden."""
    normalized = str(code or "").strip().upper()
    country = pycountry.countries.get(alpha_2=normalized)
    
    return country.name if country else ""


__all__ = [
    "COUNTRY_OPTIONS",
    "country_name_for_code",
]
