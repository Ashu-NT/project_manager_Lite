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
        self._lock: RLock = RLock()

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
        stale_callbacks: list[Callable[[T], None]] = []
        for callback in subscribers:
            try:
                callback(payload)
            except RuntimeError as exc:
                # Qt-bound methods can outlive their QObject and raise:
                # "Internal C++ object (...) already deleted."
                # Auto-prune these subscribers to keep domain events resilient.
                msg = str(exc).lower()
                if "already deleted" in msg or "has been deleted" in msg:
                    stale_callbacks.append(callback)
                    continue
                raise
            except ReferenceError:
                stale_callbacks.append(callback)
        if stale_callbacks:
            with self._lock:
                for callback in stale_callbacks:
                    if callback in self._subscribers:
                        self._subscribers.remove(callback)
