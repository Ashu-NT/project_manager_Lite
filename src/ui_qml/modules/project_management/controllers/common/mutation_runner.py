from __future__ import annotations

import logging
from typing import Callable

from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer

from src.core.platform.common.exceptions import ConcurrencyError, DomainError, ValidationError

logger = logging.getLogger(__name__)


def run_mutation(
    *,
    operation: Callable[[], None],
    success_message: str,
    on_success: Callable[[], None],
    set_is_busy,
    set_error_message,
    set_feedback_message,
    safe_errors: bool = False,
    safe_validation_message: str = "Review the highlighted resource fields and try again.",
    safe_validation_code: str = "RESOURCE_INPUT_INVALID",
    safe_failure_message: str = "The resource change could not be completed. Try again or reload the record.",
    safe_failure_code: str = "RESOURCE_MUTATION_FAILED",
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
            message = str(exc)
            code = str(getattr(exc, "code", "") or "")
            category = "unexpected"
            field_errors: dict[str, str] = {}
            if isinstance(exc, ConcurrencyError):
                category = "conflict"
            elif isinstance(exc, ValidationError):
                category = "validation"
            elif isinstance(exc, DomainError):
                category = "business"
            elif safe_errors and callable(getattr(exc, "errors", None)):
                category = "validation"
                for item in exc.errors():
                    location = item.get("loc") or ()
                    field = str(location[-1]) if location else "form"
                    field_errors[field] = str(item.get("msg") or "Invalid value.")
                message = safe_validation_message
                code = safe_validation_code
            elif safe_errors and isinstance(exc, (TypeError, ValueError)):
                category = "validation"
                message = safe_validation_message
                code = safe_validation_code
            elif safe_errors:
                message = safe_failure_message
                code = safe_failure_code
            set_feedback_message("")
            set_error_message(message)
            payload = {
                "ok": False,
                "message": message,
                "code": code,
                "category": category,
                "fieldErrors": field_errors,
                "conflict": category == "conflict",
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
