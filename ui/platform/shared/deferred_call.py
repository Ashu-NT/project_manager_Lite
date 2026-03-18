from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer


class DeferredCall(QObject):
    """Coalesce repeated UI work into a single delayed callback."""

    def __init__(
        self,
        parent: QObject | None,
        callback: Callable[[], None],
        *,
        delay_ms: int = 0,
    ) -> None:
        super().__init__(parent)
        self._callback = callback
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(max(0, int(delay_ms)))
        self._timer.timeout.connect(self._run)

    def trigger(self) -> None:
        self._timer.start()

    def cancel(self) -> None:
        self._timer.stop()

    def is_pending(self) -> bool:
        return self._timer.isActive()

    def _run(self) -> None:
        self._callback()


__all__ = ["DeferredCall"]
