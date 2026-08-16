from __future__ import annotations

from src.ui_qml.platform.controllers.common import run_admin_action

from .refresh import refresh_after_organization_change


def create_organization(controller, payload: dict) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._organization_controller.createOrganization(payload),
        on_success=lambda: refresh_after_organization_change(controller),
    )


def update_organization(controller, payload: dict) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._organization_controller.updateOrganization(payload),
        on_success=lambda: refresh_after_organization_change(controller),
    )


def set_active_organization(controller, organization_id: str) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._organization_controller.setActiveOrganization(
            organization_id
        ),
        on_success=lambda: refresh_after_organization_change(controller),
    )


__all__ = ["create_organization", "set_active_organization", "update_organization"]
