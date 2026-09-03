"""Process-local mutation hints consumed by current desktop workspace controllers.

Finance mutation families use targeted project/organization payloads and have both production
producers and the Finance destination-cache consumer. These hints never replace domain truth;
they only mark authoritative read projections stale after a successful commit.
"""

from dataclasses import dataclass, field, fields

from src.core.shared.events.signal import Signal


@dataclass
class DomainEvents:
    project_changed: Signal[str] = field(default_factory=Signal)
    tasks_changed: Signal[str] = field(default_factory=Signal)
    timesheet_periods_changed: Signal[str] = field(default_factory=Signal)
    budgets_changed: Signal[str] = field(default_factory=Signal)
    billing_preparations_changed: Signal[str] = field(default_factory=Signal)
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
