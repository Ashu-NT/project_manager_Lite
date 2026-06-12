from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import run_mutation


def generate_entity_code(controller, entity_type: str, payload: dict[str, object]) -> str:
    if (entity_type or "").strip().lower() != "register":
        return ""
    try:
        return controller._register_workspace_presenter.suggest_code(dict(payload))
    except Exception as exc:
        controller._set_error_message(str(exc))
        return ""


def create_entry(controller, payload: dict[str, object]) -> dict[str, object]:
    return run_mutation(
        operation=lambda: controller._register_workspace_presenter.create_entry(dict(payload)),
        success_message="Register entry created.",
        on_success=controller._request_domain_refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def update_entry(controller, payload: dict[str, object]) -> dict[str, object]:
    return run_mutation(
        operation=lambda: controller._register_workspace_presenter.update_entry(dict(payload)),
        success_message="Register entry updated.",
        on_success=controller._request_domain_refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def delete_entry(controller, entry_id: str) -> dict[str, object]:
    return run_mutation(
        operation=lambda: controller._register_workspace_presenter.delete_entry(entry_id),
        success_message="Register entry deleted.",
        on_success=controller._request_domain_refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


__all__ = ["create_entry", "delete_entry", "generate_entity_code", "update_entry"]
