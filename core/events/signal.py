from __future__ import annotations

from threading import RLock
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


class Signal(Generic[T]):
    """
    Minimal framework-agnostic signal/slot primitive.
    Implements the Observer pattern for domain events without Qt coupling.
    """

    def __init__(self) -> None:
        self._subscribers: list[Callable[[T], None]] = []
        self._lock = RLock()

    def connect(self, callback: Callable[[T], None]) -> None:
        with self._lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)

    def disconnect(self, callback: Callable[[T], None]) -> None:
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    def emit(self, payload: T) -> None:
        with self._lock:
            subscribers = list(self._subscribers)
        for callback in subscribers:
            callback(payload)
