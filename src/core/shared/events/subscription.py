from __future__ import annotations

from typing import Protocol


class Subscription(Protocol):
    def dispose(self) -> None: ...


__all__ = ["Subscription"]
