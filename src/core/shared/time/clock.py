"""General-purpose time abstraction -- not events-specific, but used by
`RecordsDomainEvents`-adopting aggregates to stamp `occurred_at` on the DomainEvents they
record. Contract only; the concrete implementation (`SystemClock`) lives in
`src/infra/time/system_clock.py`, added when a real consumer needs it (P4/P5), not here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


__all__ = ["Clock"]
