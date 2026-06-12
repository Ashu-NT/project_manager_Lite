from __future__ import annotations

from datetime import UTC, datetime, timedelta


def within_period(iso_value: str, period_key: str) -> bool:
    if not iso_value or period_key == "all":
        return True
    try:
        observed = datetime.fromisoformat(iso_value.replace("Z", "+00:00"))
    except ValueError:
        return True
    now = datetime.now(UTC)
    if period_key == "24h":
        return observed >= now - timedelta(hours=24)
    if period_key == "7d":
        return observed >= now - timedelta(days=7)
    if period_key == "30d":
        return observed >= now - timedelta(days=30)
    return True
