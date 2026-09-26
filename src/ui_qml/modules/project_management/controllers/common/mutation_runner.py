from __future__ import annotations

import logging
from collections.abc import Callable

from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer

from src.core.platform.common.exceptions import (
    ConcurrencyError,
    DomainError,
    ValidationError,
)

logger = logging.getLogger(__name__)

_DEFAULT_VALIDATION_MESSAGE = "Review the highlighted fields and try again."
_DEFAULT_VALIDATION_CODE = "MUTATION_INPUT_INVALID"
_DEFAULT_FAILURE_MESSAGE = "The change could not be completed. Try again or refresh the workspace."
_DEFAULT_FAILURE_CODE = "MUTATION_FAILED"


def run_mutation(
    *,
    operation: Callable[[], None],
    success_message: str,
    on_success: Callable[[], None],
    set_is_busy,
    set_error_message,
    set_feedback_message,
    safe_validation_message: str = _DEFAULT_VALIDATION_MESSAGE,
    safe_validation_code: str = _DEFAULT_VALIDATION_CODE,
    safe_failure_message: str = _DEFAULT_FAILURE_MESSAGE,
    safe_failure_code: str = _DEFAULT_FAILURE_CODE,
) -> dict[str, object]:
    """Run a single workspace mutation and translate its outcome into a UI-safe result.
    """
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
            elif callable(getattr(exc, "errors", None)):
                category = "validation"
                for item in exc.errors():
                    location = item.get("loc") or ()
                    field = str(location[-1]) if location else "form"
                    field_errors[field] = str(item.get("msg") or "Invalid value.")
                message = safe_validation_message
                code = safe_validation_code
            elif isinstance(exc, (TypeError, ValueError)):
                category = "validation"
                message = safe_validation_message
                code = safe_validation_code
            else:
                # Not one of this codebase's own DomainError-family types --
                # its raw text (SQL, stack fragments, internal identifiers,
                # exception class names) must never reach the UI. The full
                # exception is already logged above.
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
