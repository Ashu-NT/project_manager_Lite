from __future__ import annotations

from src.ui_qml.platform.controllers.common import serialize_operation_result

from .admin_action_runner import run_admin_result_action
from .admin_calendar_command_builders import (
    build_calendar_create_command,
    build_calendar_update_command,
    build_exception_create_command,
    build_recurring_event_create_command,
    dispatch_calendar_assign,
)
from .admin_refresh_service import refresh_after_calendar_change


def update_calendar(controller, payload: dict) -> dict[str, object]:
    return run_admin_result_action(
        controller,
        operation=lambda: controller._calendar_controller.updateCalendar(dict(payload)),
        success_message="Working calendar updated.",
        on_success=lambda: refresh_after_calendar_change(controller),
    )


def add_calendar_holiday(controller, payload: dict) -> dict[str, object]:
    return run_admin_result_action(
        controller,
        operation=lambda: controller._calendar_controller.addCalendarHoliday(dict(payload)),
        success_message="Calendar exception added.",
        on_success=lambda: refresh_after_calendar_change(controller),
    )


def delete_calendar_holiday(controller, holiday_id: str) -> dict[str, object]:
    return run_admin_result_action(
        controller,
        operation=lambda: controller._calendar_controller.deleteCalendarHoliday(holiday_id),
        success_message="Calendar exception removed.",
        on_success=lambda: refresh_after_calendar_change(controller),
    )


def calculate_calendar_working_days(controller, payload: dict) -> dict[str, object]:
    controller._set_is_busy(True)
    controller._set_error_message("")
    try:
        result = controller._calendar_controller.calculateCalendarWorkingDays(dict(payload))
        if (
            result is not None
            and getattr(result, "ok", False)
            and getattr(result, "data", None) is not None
        ):
            message = controller._calendar_controller.formatCalculationResult(result.data)
            payload_map = {
                "ok": True,
                "category": "",
                "code": "",
                "message": message,
            }
            controller._set_feedback_message("")
            controller._set_operation_result(payload_map)
            return dict(payload_map)
        payload_map = serialize_operation_result(
            result,
            success_message="Working-day calculation completed.",
        )
        controller._set_feedback_message("")
        controller._set_error_message(str(payload_map.get("message", "")))
        controller._set_operation_result(payload_map)
        return dict(payload_map)
    finally:
        controller._set_is_busy(False)


def create_enterprise_calendar(controller, payload: dict) -> dict[str, object]:
    return run_admin_result_action(
        controller,
        operation=lambda: controller._enterprise_calendar_api.create_calendar(
            build_calendar_create_command(payload)
        ) if controller._enterprise_calendar_api else None,
        success_message="Calendar created.",
        on_success=lambda: refresh_after_calendar_change(controller),
    )


def update_enterprise_calendar(controller, payload: dict) -> dict[str, object]:
    return run_admin_result_action(
        controller,
        operation=lambda: controller._enterprise_calendar_api.update_calendar(
            build_calendar_update_command(payload)
        ) if controller._enterprise_calendar_api else None,
        success_message="Calendar updated.",
        on_success=lambda: refresh_after_calendar_change(controller),
    )


def add_calendar_exception(controller, payload: dict) -> dict[str, object]:
    return run_admin_result_action(
        controller,
        operation=lambda: controller._enterprise_calendar_api.add_exception(
            build_exception_create_command(payload)
        ) if controller._enterprise_calendar_api else None,
        success_message="Calendar exception added.",
        on_success=lambda: refresh_after_calendar_change(controller),
    )


def add_calendar_recurring_event(controller, payload: dict) -> dict[str, object]:
    return run_admin_result_action(
        controller,
        operation=lambda: controller._enterprise_calendar_api.add_recurring_event(
            build_recurring_event_create_command(payload)
        ) if controller._enterprise_calendar_api else None,
        success_message="Recurring event added.",
        on_success=lambda: refresh_after_calendar_change(controller),
    )


def delete_calendar_exception(controller, exception_id: str) -> dict[str, object]:
    return run_admin_result_action(
        controller,
        operation=lambda: controller._enterprise_calendar_api.delete_exception(exception_id)
        if controller._enterprise_calendar_api
        else None,
        success_message="Calendar exception removed.",
        on_success=lambda: refresh_after_calendar_change(controller),
    )


def delete_calendar_recurring_event(controller, event_id: str) -> dict[str, object]:
    return run_admin_result_action(
        controller,
        operation=lambda: controller._enterprise_calendar_api.delete_recurring_event(event_id)
        if controller._enterprise_calendar_api
        else None,
        success_message="Recurring event removed.",
        on_success=lambda: refresh_after_calendar_change(controller),
    )


def assign_calendar(controller, payload: dict) -> dict[str, object]:
    entity_type = str(payload.get("entityType", "")).lower()
    return run_admin_result_action(
        controller,
        operation=lambda: dispatch_calendar_assign(controller, payload, entity_type),
        success_message="Calendar assigned.",
        on_success=lambda: refresh_after_calendar_change(controller),
    )


def remove_calendar_assignment(
    controller, assignment_id: str, entity_type: str
) -> dict[str, object]:
    return run_admin_result_action(
        controller,
        operation=lambda: controller._enterprise_calendar_api.remove_assignment(
            assignment_id,
            entity_type,
        )
        if controller._enterprise_calendar_api
        else None,
        success_message="Calendar assignment removed.",
        on_success=lambda: refresh_after_calendar_change(controller),
    )


__all__ = [
    "add_calendar_exception",
    "add_calendar_holiday",
    "add_calendar_recurring_event",
    "assign_calendar",
    "calculate_calendar_working_days",
    "create_enterprise_calendar",
    "delete_calendar_exception",
    "delete_calendar_holiday",
    "delete_calendar_recurring_event",
    "remove_calendar_assignment",
    "update_calendar",
    "update_enterprise_calendar",
]
