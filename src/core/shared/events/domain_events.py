from dataclasses import dataclass, fields

from src.core.shared.events.signal import Signal


@dataclass
class DomainEvents:
    """P46B: the last legacy Signal field (`auth_changed`) is now deleted -- this dataclass is
    intentionally empty and slated for full removal once every test that still constructs/asserts
    against it (see `docs/architecture/event-modernization-plan.md`'s P46B entry) is converged
    onto the canonical typed-DomainEvent/ViewInvalidation architecture. Not a compatibility shell
    kept for its own sake -- a disclosed, in-progress deletion, not a permanent shape."""

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
