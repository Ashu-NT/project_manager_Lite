from __future__ import annotations

from src.core.shared.events.domain_event import DomainEvent


class RecordsDomainEvents:
    _pending_domain_events: list[DomainEvent]

    def _ensure_event_storage(self) -> None:
        if not hasattr(self, "_pending_domain_events"):
            self._pending_domain_events = []

    def _record_event(self, event: DomainEvent) -> None:
        self._ensure_event_storage()
        self._pending_domain_events.append(event)

    def domain_events(self) -> tuple[DomainEvent, ...]:
        """Read-only snapshot. Does not clear anything."""
        self._ensure_event_storage()
        return tuple(self._pending_domain_events)

    def clear_domain_events(self) -> None:
        """Called by the unit of work only after commit has succeeded."""
        self._ensure_event_storage()
        self._pending_domain_events.clear()


__all__ = ["RecordsDomainEvents"]
