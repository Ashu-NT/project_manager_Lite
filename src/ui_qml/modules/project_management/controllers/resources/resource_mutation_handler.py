from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import (
    run_mutation,
    safe_error_message,
)


def generate_entity_code(controller, entity_type: str, payload: dict[str, object]) -> str:
    if (entity_type or "").strip().lower() != "resource":
        return ""
    try:
        return controller._resources_workspace_presenter.suggest_code(dict(payload))
    except Exception as exc:
        controller._set_error_message(
            safe_error_message(exc, safe_message="A resource code could not be suggested.")
        )
        return ""


def create_resource(controller, payload: dict[str, object]) -> dict[str, object]:
    return run_mutation(
        operation=lambda: controller._resources_workspace_presenter.create_resource(dict(payload)),
        success_message="Resource created.",
        on_success=controller._request_domain_refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
        safe_validation_message="Review the highlighted resource fields and try again.",
        safe_validation_code="RESOURCE_INPUT_INVALID",
        safe_failure_message="The resource change could not be completed. Try again or reload the record.",
        safe_failure_code="RESOURCE_MUTATION_FAILED",
    )


def update_resource(controller, payload: dict[str, object]) -> dict[str, object]:
    return run_mutation(
        operation=lambda: controller._resources_workspace_presenter.update_resource(dict(payload)),
        success_message="Resource updated.",
        on_success=controller._request_domain_refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
        safe_validation_message="Review the highlighted resource fields and try again.",
        safe_validation_code="RESOURCE_INPUT_INVALID",
        safe_failure_message="The resource change could not be completed. Try again or reload the record.",
        safe_failure_code="RESOURCE_MUTATION_FAILED",
    )


def deactivate_resource(
    controller,
    resource_id: str,
    expected_version: int,
) -> dict[str, object]:
    return run_mutation(
        operation=lambda: controller._resources_workspace_presenter.deactivate_resource(
            resource_id,
            expected_version=expected_version,
        ),
        success_message="Resource deactivated.",
        on_success=controller._request_domain_refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
        safe_validation_message="Review the highlighted resource fields and try again.",
        safe_validation_code="RESOURCE_INPUT_INVALID",
        safe_failure_message="The resource change could not be completed. Try again or reload the record.",
        safe_failure_code="RESOURCE_MUTATION_FAILED",
    )


def reactivate_resource(
    controller,
    resource_id: str,
    expected_version: int,
) -> dict[str, object]:
    return run_mutation(
        operation=lambda: controller._resources_workspace_presenter.reactivate_resource(
            resource_id,
            expected_version,
        ),
        success_message="Resource reactivated.",
        on_success=controller._request_domain_refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
        safe_validation_message="Review the highlighted resource fields and try again.",
        safe_validation_code="RESOURCE_INPUT_INVALID",
        safe_failure_message="The resource change could not be completed. Try again or reload the record.",
        safe_failure_code="RESOURCE_MUTATION_FAILED",
    )


__all__ = [
    "create_resource",
    "deactivate_resource",
    "generate_entity_code",
    "reactivate_resource",
    "update_resource",
]
