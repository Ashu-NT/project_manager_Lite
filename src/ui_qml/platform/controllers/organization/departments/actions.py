from __future__ import annotations

from src.ui_qml.platform.controllers.common import run_admin_action

from .refresh import refresh_after_department_change


def create_department(controller, payload: dict) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._department_controller.createDepartment(payload),
        on_success=lambda: refresh_after_department_change(controller),
    )


def update_department(controller, payload: dict) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._department_controller.updateDepartment(payload),
        on_success=lambda: refresh_after_department_change(controller),
    )


def toggle_department_active(controller, department_id: str) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._department_controller.toggleDepartmentActive(department_id),
        on_success=lambda: refresh_after_department_change(controller),
    )


__all__ = ["create_department", "toggle_department_active", "update_department"]
