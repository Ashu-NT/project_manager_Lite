from __future__ import annotations

from typing import Callable

from .serializers import serialize_operation_result


def run_mutation(
    *,
    operation: Callable[[], object],
    success_message: str,
    on_success: Callable[[], None],
    set_is_busy,
    set_error_message,
    set_operation_result,
    set_feedback_message,
    success_result_handler: Callable[[object], None] | None = None,
) -> dict[str, object]:
    set_is_busy(True)
    set_error_message("")
    result = operation()
    payload = serialize_operation_result(result, success_message=success_message)
    set_operation_result(payload)
    if payload["ok"]:
        set_feedback_message(str(payload["message"]))
        if success_result_handler is not None:
            success_result_handler(result)
        on_success()
    else:
        set_feedback_message("")
        set_error_message(str(payload["message"]))
    set_is_busy(False)
    return dict(payload)


__all__ = ["run_mutation"]