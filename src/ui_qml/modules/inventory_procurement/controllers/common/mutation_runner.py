from __future__ import annotations

import logging
from typing import Callable

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
    set_is_busy(True)
    set_error_message("")
    try:
        operation()
    except Exception as exc:
        logger.exception("Inventory workspace mutation failed.")
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
    return payload


__all__ = ["run_mutation"]
