"""A minimal, injectable time source for PM application services -- lets
rate-card seeding/supersession and snapshot timestamps be deterministic
in tests instead of calling ``datetime.now()`` directly."""

from __future__ import annotations

from datetime import UTC, date, datetime


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)

    def today(self) -> date:
        return datetime.now(UTC).date()


__all__ = [ "SystemClock"]
