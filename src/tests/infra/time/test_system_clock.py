from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.core.shared.time.clock import Clock
from src.infra.time.system_clock import SystemClock


def test_system_clock_returns_a_timezone_aware_utc_datetime() -> None:
    clock = SystemClock()
    now = clock.now()

    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(0)


def test_system_clock_reflects_real_wall_clock_time() -> None:
    before = datetime.now(timezone.utc)
    now = SystemClock().now()
    after = datetime.now(timezone.utc)

    assert before <= now <= after


def test_system_clock_satisfies_the_clock_protocol_structurally() -> None:
    clock: Clock = SystemClock()
    assert callable(clock.now)
    assert isinstance(clock.now(), datetime)
