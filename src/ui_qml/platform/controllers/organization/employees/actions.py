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


__all__ = ["create_employee", "toggle_employee_active", "update_employee"]
