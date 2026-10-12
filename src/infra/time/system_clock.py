"""The concrete `Clock` implementation -- real, timezone-aware UTC wall-clock time. No
timezone/business-calendar infrastructure; that is explicitly out of scope."""

from __future__ import annotations

from datetime import UTC, datetime


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


__all__ = ["SystemClock"]
