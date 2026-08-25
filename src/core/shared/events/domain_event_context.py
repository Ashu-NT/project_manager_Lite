"""ADR-005 §5 (Event Metadata Decision): dispatch/execution metadata, kept separate from
business-fact data.

A `DomainEvent` dataclass carries only business-fact fields. `DomainEventContext` carries
dispatch-time tracing metadata, owned by a `UnitOfWork` for the lifetime of one transaction --
never embedded in the event itself, never coupled to ADR-PF-011's durable `IntegrationEventEnvelope`.

Deliberately excludes `actor_id` (a business fact needing "who did this" names its own field,
e.g. `decided_by_user_id` -- see ADR-005 §5) and `schema_version` (an in-process event never
crosses a durable boundary, so there is no reader that could run different code than the writer
-- see ADR-005 §11; `schema_version` remains exclusively an Integration Event concern).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEventContext:
    correlation_id: str
    causation_id: str | None = None
    command_id: str | None = None


__all__ = ["DomainEventContext"]
