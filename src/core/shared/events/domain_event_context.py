from __future__ import annotations

from dataclasses import dataclass

# Dispatch-time tracing metadata, owned by a UnitOfWork for the lifetime of
# one transaction -- kept separate from DomainEvent's business-fact fields.


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEventContext:
    correlation_id: str
    causation_id: str | None = None
    command_id: str | None = None


__all__ = ["DomainEventContext"]
