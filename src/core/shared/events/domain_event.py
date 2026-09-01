"""ADR-005 §4: the minimal shared marker for a Domain Event -- a business fact that occurred.

Typing contract only. Zero business vocabulary, zero tenant/organization vocabulary (those are
per-event fields on each module's own concrete event dataclasses, not part of this marker,
since a genuinely platform-wide event legitimately has neither).
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class DomainEvent(Protocol):
    """`occurred_at` is declared as a read-only property, not a plain mutable attribute: every
    concrete event is a frozen dataclass, readable but never writable after construction, and
    PEP 544 structural variance requires a Protocol's plain attribute to be read-write. A
    read-only property member is satisfied by a frozen dataclass field's read access without
    requiring write access -- this is a type-annotation-only change with no runtime effect
    (Protocol stub bodies are never executed)."""

    @property
    def occurred_at(self) -> datetime: ...


__all__ = ["DomainEvent"]
