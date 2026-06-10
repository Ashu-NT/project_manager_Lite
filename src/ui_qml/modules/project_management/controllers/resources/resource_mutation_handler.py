from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import run_mutation


def generate_entity_code(controller, entity_type: str, payload: dict[str, object]) -> str:
    if (entity_type or "").strip().lower() != "resource":
        return ""
    try:
        return controller._resources_workspace_presenter.suggest_code(dict(payload))
    except Exception as exc:
        controller._set_error_message(str(exc))
        return ""


def create_resource(controller, payload: dict[str, object]) -> dict[str, object]:
    return run_mutation(
        operation=lambda: controller._resources_workspace_presenter.create_resource(dict(payload)),
        success_message="Resource created.",
        on_success=controller._request_domain_refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def update_resource(controller, payload: dict[str, object]) -> dict[str, object]:
    return run_mutation(
        operation=lambda: controller._resources_workspace_presenter.update_resource(dict(payload)),
        success_message="Resource updated.",
        on_success=controller._request_domain_refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def toggle_resource_active(
    controller,
    resource_id: str,
    expected_version: int,
) -> dict[str, object]:
    return run_mutation(
        operation=lambda: controller._resources_workspace_presenter.toggle_resource_active(
            resource_id,
            expected_version=expected_version,
        ),
        success_message="Resource availability updated.",
        on_success=controller._request_domain_refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def delete_resource(controller, resource_id: str) -> dict[str, object]:
    return run_mutation(
        operation=lambda: controller._resources_workspace_presenter.delete_resource(resource_id),
        success_message="Resource deleted.",
        on_success=controller._request_domain_refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


__all__ = [
    "create_resource",
    "delete_resource",
    "generate_entity_code",
    "toggle_resource_active",
    "update_resource",
]
