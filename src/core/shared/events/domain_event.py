from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class DomainEvent(Protocol):

    @property
    def occurred_at(self) -> datetime: ...


__all__ = ["DomainEvent"]
