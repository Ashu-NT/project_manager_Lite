from __future__ import annotations

from src.ui_qml.modules.maintenance.controllers.common import run_mutation


def create_location(controller, payload: dict) -> dict:
    return run_mutation(
        operation=lambda: controller._assets_workspace_presenter.create_location(
            dict(payload)
        ),
        success_message="Location created.",
        on_success=controller.refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def update_location(controller, payload: dict) -> dict:
    return run_mutation(
        operation=lambda: controller._assets_workspace_presenter.update_location(
            dict(payload)
        ),
        success_message="Location updated.",
        on_success=controller.refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def toggle_location_active(
    controller, location_id: str, expected_version: int
) -> dict:
    return run_mutation(
        operation=lambda: controller._assets_workspace_presenter.toggle_location_active(
            location_id, expected_version=expected_version
        ),
        success_message="Location active state updated.",
        on_success=controller.refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def create_system(controller, payload: dict) -> dict:
    return run_mutation(
        operation=lambda: controller._assets_workspace_presenter.create_system(
            dict(payload)
        ),
        success_message="System created.",
        on_success=controller.refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def update_system(controller, payload: dict) -> dict:
    return run_mutation(
        operation=lambda: controller._assets_workspace_presenter.update_system(
            dict(payload)
        ),
        success_message="System updated.",
        on_success=controller.refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def toggle_system_active(
    controller, system_id: str, expected_version: int
) -> dict:
    return run_mutation(
        operation=lambda: controller._assets_workspace_presenter.toggle_system_active(
            system_id, expected_version=expected_version
        ),
        success_message="System active state updated.",
        on_success=controller.refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def create_asset(controller, payload: dict) -> dict:
    return run_mutation(
        operation=lambda: controller._assets_workspace_presenter.create_asset(
            dict(payload)
        ),
        success_message="Asset created.",
        on_success=controller.refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def update_asset(controller, payload: dict) -> dict:
    return run_mutation(
        operation=lambda: controller._assets_workspace_presenter.update_asset(
            dict(payload)
        ),
        success_message="Asset updated.",
        on_success=controller.refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def toggle_asset_active(
    controller, asset_id: str, expected_version: int
) -> dict:
    return run_mutation(
        operation=lambda: controller._assets_workspace_presenter.toggle_asset_active(
            asset_id, expected_version=expected_version
        ),
        success_message="Asset active state updated.",
        on_success=controller.refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def create_component(controller, payload: dict) -> dict:
    return run_mutation(
        operation=lambda: controller._assets_workspace_presenter.create_component(
            dict(payload)
        ),
        success_message="Component created.",
        on_success=controller.refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def update_component(controller, payload: dict) -> dict:
    return run_mutation(
        operation=lambda: controller._assets_workspace_presenter.update_component(
            dict(payload)
        ),
        success_message="Component updated.",
        on_success=controller.refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def toggle_component_active(
    controller, component_id: str, expected_version: int
) -> dict:
    return run_mutation(
        operation=lambda: controller._assets_workspace_presenter.toggle_component_active(
            component_id, expected_version=expected_version
        ),
        success_message="Component active state updated.",
        on_success=controller.refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )
