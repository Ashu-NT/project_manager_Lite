from __future__ import annotations

from src.ui_qml.platform.controllers.common import run_admin_action

from .refresh import refresh_after_employee_change


def create_employee(controller, payload: dict) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._employee_controller.createEmployee(payload),
        on_success=lambda: refresh_after_employee_change(controller),
    )


def update_employee(controller, payload: dict) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._employee_controller.updateEmployee(payload),
        on_success=lambda: refresh_after_employee_change(controller),
    )


def toggle_employee_active(controller, employee_id: str) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._employee_controller.toggleEmployeeActive(employee_id),
        on_success=lambda: refresh_after_employee_change(controller),
    )


def activate_employee(controller, employee_id: str) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._employee_controller.activateEmployee(employee_id),
        on_success=lambda: refresh_after_employee_change(controller),
    )


def deactivate_employee(controller, employee_id: str) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._employee_controller.deactivateEmployee(employee_id),
        on_success=lambda: refresh_after_employee_change(controller),
    )


def link_employee_user_account(controller, employee_id: str, user_id: str) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._employee_controller.linkEmployeeUserAccount(employee_id, user_id),
        on_success=lambda: refresh_after_employee_change(controller),
    )


def unlink_employee_user_account(controller, employee_id: str) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._employee_controller.unlinkEmployeeUserAccount(employee_id),
        on_success=lambda: refresh_after_employee_change(controller),
    )


__all__ = [
    "activate_employee",
    "create_employee",
    "deactivate_employee",
    "link_employee_user_account",
    "toggle_employee_active",
    "unlink_employee_user_account",
    "update_employee",
]
