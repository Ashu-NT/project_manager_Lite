from __future__ import annotations

import logging
from typing import Callable

from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer

logger = logging.getLogger(__name__)


def run_mutation(
    *,
    operation: Callable[[], None],
    success_message: str,
    on_success: Callable[[], None],
    set_is_busy,
    set_error_message,
    set_feedback_message,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "ok": False,
        "message": "",
    }

    def _perform_mutation() -> None:
        nonlocal payload
        try:
            operation()
        except Exception as exc:
            logger.exception("Workspace mutation failed.")
            set_feedback_message("")
            set_error_message(str(exc))
            payload = {
                "ok": False,
                "message": str(exc),
            }
        else:
            set_feedback_message(success_message)
            on_success()
            payload = {
                "ok": True,
                "message": success_message,
            }
        finally:
            set_is_busy(False)

    set_is_busy(True)
    set_error_message("")
    app = QCoreApplication.instance()
    if app is None:
        _perform_mutation()
        return payload

    loop = QEventLoop()

    def _run_and_quit() -> None:
        try:
            _perform_mutation()
        finally:
            if loop.isRunning():
                loop.quit()

    QTimer.singleShot(0, _run_and_quit)
    loop.exec()
    return payload


__all__ = ["run_mutation"]
