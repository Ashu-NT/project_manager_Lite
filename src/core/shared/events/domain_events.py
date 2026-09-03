"""Process-local mutation hints consumed by current desktop workspace controllers.

These hints never replace domain truth; they only mark authoritative read projections stale
after a successful commit.

P39: Finance module modernization is complete -- zero Finance-owned legacy Signal fields remain
here (the last, `billing_preparations_changed`, is retired). Every Finance capability now
publishes typed DomainEvents through `PostCommitEventPublisher`/`ViewInvalidationChannel`
instead. See `test_finance_zero_legacy_signal_guard` (platform test suite) for the permanent
architecture assertion that this must not regress.
"""

from dataclasses import dataclass, field, fields

from src.core.shared.events.signal import Signal


@dataclass
class DomainEvents:
    project_changed: Signal[str] = field(default_factory=Signal)
    tasks_changed: Signal[str] = field(default_factory=Signal)
    timesheet_periods_changed: Signal[str] = field(default_factory=Signal)
    register_changed: Signal[str] = field(default_factory=Signal)
    auth_changed: Signal[str] = field(default_factory=Signal)
    collaboration_changed: Signal[str] = field(default_factory=Signal)
    portfolio_changed: Signal[str] = field(default_factory=Signal)

    def reset(self) -> None:
        for signal_field in fields(self):
            signal = getattr(self, signal_field.name)
            if isinstance(signal, Signal):
                signal.clear()


domain_events = DomainEvents()


__all__ = [
    "DomainEvents",
    "domain_events",
]
