from __future__ import annotations

from datetime import date as _date


def parse_iso_date(v: object) -> _date | None:
    if not v:
        return None
    try:
        return _date.fromisoformat(str(v).strip())
    except (ValueError, TypeError):
        return None


__all__ = ["parse_iso_date"]
