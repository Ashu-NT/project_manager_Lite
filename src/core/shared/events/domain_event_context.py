from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEventContext:
    correlation_id: str
    causation_id: str | None = None
    command_id: str | None = None


__all__ = ["DomainEventContext"]
