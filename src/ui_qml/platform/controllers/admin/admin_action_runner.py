from __future__ import annotations

from typing import Callable

from src.ui_qml.platform.controllers.common import serialize_operation_result


def run_admin_action(
    controller,
    *,
    action: Callable[[], dict[str, object]],
    on_success: Callable[[], None],
) -> dict[str, object]:
    controller._set_is_busy(True)
    controller._set_error_message("")
    try:
        result = dict(action())
        controller._set_operation_result(result)
        if result.get("ok"):
            controller._set_feedback_message(str(result.get("message", "")))
            on_success()
        else:
            controller._set_feedback_message("")
            controller._set_error_message(str(result.get("message", "")))
        return result
    finally:
        controller._set_is_busy(False)


def run_admin_result_action(
    controller,
    *,
    operation,
    success_message: str,
    on_success: Callable[[], None],
) -> dict[str, object]:
    controller._set_is_busy(True)
    controller._set_error_message("")
    try:
        result = operation()
        payload = serialize_operation_result(result, success_message=success_message)
        controller._set_operation_result(payload)
        if payload.get("ok"):
            controller._set_feedback_message(str(payload.get("message", "")))
            on_success()
        else:
            controller._set_feedback_message("")
            controller._set_error_message(str(payload.get("message", "")))
        return dict(payload)
    finally:
        controller._set_is_busy(False)


__all__ = ["run_admin_action", "run_admin_result_action"]
