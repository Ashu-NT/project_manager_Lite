from __future__ import annotations

from src.ui_qml.platform.controllers.common import run_admin_action

from .refresh import refresh_after_party_change


def create_party(controller, payload: dict) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._party_controller.createParty(payload),
        on_success=lambda: refresh_after_party_change(controller),
    )


def update_party(controller, payload: dict) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._party_controller.updateParty(payload),
        on_success=lambda: refresh_after_party_change(controller),
    )


def toggle_party_active(controller, party_id: str) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._party_controller.togglePartyActive(party_id),
        on_success=lambda: refresh_after_party_change(controller),
    )


def activate_party(controller, party_id: str) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._party_controller.activateParty(party_id),
        on_success=lambda: refresh_after_party_change(controller),
    )


def deactivate_party(controller, party_id: str) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._party_controller.deactivateParty(party_id),
        on_success=lambda: refresh_after_party_change(controller),
    )


__all__ = [
    "activate_party",
    "create_party",
    "deactivate_party",
    "toggle_party_active",
    "update_party",
]
