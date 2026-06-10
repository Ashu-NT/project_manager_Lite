from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.controllers.common import run_mutation


def generate_entity_code(ctrl, entity_type: str, payload: dict[str, object]) -> str:
    key = (entity_type or "").strip().lower()
    try:
        if key == "storeroom":
            return ctrl._inventory_workspace_presenter.suggest_storeroom_code(
                dict(payload)
            )
    except Exception as exc:  # noqa: BLE001 - surface to dialog/banner
        ctrl._set_error_message(str(exc))
    return ""


def create_storeroom(ctrl, payload: dict[str, object]) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._inventory_workspace_presenter.create_storeroom(
            dict(payload)
        ),
        success_message="Storeroom created.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )


def update_storeroom(ctrl, payload: dict[str, object]) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._inventory_workspace_presenter.update_storeroom(
            dict(payload)
        ),
        success_message="Storeroom updated.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )


def toggle_storeroom_active(
    ctrl, storeroom_id: str, expected_version: int = 0
) -> dict[str, object]:
    resolved_version = expected_version or None
    return run_mutation(
        operation=lambda: ctrl._inventory_workspace_presenter.toggle_storeroom_active(
            storeroom_id,
            resolved_version,
        ),
        success_message="Storeroom availability updated.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )
