"""ADR-005 §6 (Event Recording Decision): minimal aggregate event-recording behavior.

Rule: if a DomainEvent represents a business fact produced directly by an aggregate's own
state transition, the aggregate MUST record that event itself, via this mixin -- never a
convenience default for the `uow.record_event(...)` escape hatch (reserved exclusively for
facts with no single owning aggregate; that method lives on the future UnitOfWork contract,
not here).

Framework-independent: this mixin knows nothing about UnitOfWork, dispatchers, publishers,
SQLAlchemy, or UI invalidation. It only records, inspects, and clears pending events.
"""

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
