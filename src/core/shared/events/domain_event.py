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
    occurred_at: datetime


__all__ = ["DomainEvent"]
