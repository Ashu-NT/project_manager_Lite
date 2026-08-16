from __future__ import annotations

from src.ui_qml.platform.controllers.common import run_admin_action

from .refresh import refresh_after_site_change


def create_site(controller, payload: dict) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._site_controller.createSite(payload),
        on_success=lambda: refresh_after_site_change(controller),
    )


def update_site(controller, payload: dict) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._site_controller.updateSite(payload),
        on_success=lambda: refresh_after_site_change(controller),
    )


def toggle_site_active(controller, site_id: str) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._site_controller.toggleSiteActive(site_id),
        on_success=lambda: refresh_after_site_change(controller),
    )


__all__ = ["create_site", "toggle_site_active", "update_site"]
