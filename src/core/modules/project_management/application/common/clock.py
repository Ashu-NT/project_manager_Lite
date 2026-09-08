"""A minimal, injectable time source for PM application services -- lets
rate-card seeding/supersession and snapshot timestamps be deterministic
in tests instead of calling ``datetime.now()`` directly."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...
    def today(self) -> date: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)

    def today(self) -> date:
        return datetime.now(timezone.utc).date()


__all__ = ["Clock", "SystemClock"]
