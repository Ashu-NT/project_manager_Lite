"""A minimal, self-contained time source for PM application services.

Scoped to exactly one need: giving the rate-card cutover (resource rate
seeding/supersession, snapshot timestamps) a deterministic, injectable
"what time is it" instead of a hidden ``date.today()``/``datetime.now()``
call buried in business logic. This is intentionally not an attempt to
implement ADR-005's separately-proposed, not-yet-accepted ``Clock``
design — that ADR is unrelated and still proposed; this is a small,
local utility.
"""

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
