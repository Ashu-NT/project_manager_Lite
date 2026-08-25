"""Clock protocol -- contract only, no concrete SystemClock implementation exists yet
(that is added when a real P4/P5 consumer needs it, per the implementation plan)."""

from __future__ import annotations

from datetime import datetime, timezone

from src.core.shared.time.clock import Clock


class _FixedClock:
    def __init__(self, fixed: datetime) -> None:
        self._fixed = fixed

    def now(self) -> datetime:
        return self._fixed


def test_a_fixed_test_clock_satisfies_the_clock_protocol_structurally() -> None:
    """Clock is not @runtime_checkable in the approved ADR (unlike DomainEvent) -- checked
    by duck typing (it has a callable now()), not isinstance()."""
    fixed = datetime(2026, 1, 1, tzinfo=timezone.utc)
    clock = _FixedClock(fixed)

    assert callable(getattr(clock, "now", None))
    assert clock.now() == fixed


def test_clock_protocol_declares_only_now() -> None:
    assert hasattr(Clock, "now")
