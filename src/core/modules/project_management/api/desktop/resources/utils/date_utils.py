from __future__ import annotations

from datetime import date


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value).strip())
    except (ValueError, AttributeError):
        return None


__all__ = ["parse_date"]
