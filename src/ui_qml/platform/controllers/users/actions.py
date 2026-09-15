from __future__ import annotations

from src.ui_qml.platform.controllers.common import run_admin_action

from .refresh import refresh_after_user_change


def create_user(controller, payload: dict) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._user_controller.createUser(payload),
        on_success=lambda: refresh_after_user_change(controller),
    )


def update_user(controller, payload: dict) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._user_controller.updateUser(payload),
        on_success=lambda: refresh_after_user_change(controller),
    )


def toggle_user_active(controller, user_id: str) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._user_controller.toggleUserActive(user_id),
        on_success=lambda: refresh_after_user_change(controller),
    )


__all__ = ["create_user", "toggle_user_active", "update_user"]
