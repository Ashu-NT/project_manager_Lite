from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.controllers.common import run_mutation


def generate_entity_code(ctrl, entity_type: str, payload: dict) -> str:
    key = (entity_type or "").strip().lower()
    try:
        if key == "category":
            return ctrl._catalog_workspace_presenter.suggest_category_code(payload)
        if key == "item":
            return ctrl._catalog_workspace_presenter.suggest_item_code(payload)
    except Exception as exc:  # noqa: BLE001 - surface to dialog/banner
        ctrl._set_error_message(str(exc))
    return ""


def create_category(ctrl, payload: dict) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._catalog_workspace_presenter.create_category(payload),
        success_message="Category created.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )


def update_category(ctrl, payload: dict) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._catalog_workspace_presenter.update_category(payload),
        success_message="Category updated.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )


def toggle_category_active(
    ctrl, category_id: str, expected_version: int = 0
) -> dict[str, object]:
    resolved_version = expected_version or None
    return run_mutation(
        operation=lambda: ctrl._catalog_workspace_presenter.toggle_category_active(
            category_id, resolved_version
        ),
        success_message="Category availability updated.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )


def create_item(ctrl, payload: dict) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._catalog_workspace_presenter.create_item(payload),
        success_message="Item created.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )


def update_item(ctrl, payload: dict) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._catalog_workspace_presenter.update_item(payload),
        success_message="Item updated.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )


def toggle_item_active(
    ctrl, item_id: str, expected_version: int = 0
) -> dict[str, object]:
    resolved_version = expected_version or None
    return run_mutation(
        operation=lambda: ctrl._catalog_workspace_presenter.toggle_item_active(
            item_id, resolved_version
        ),
        success_message="Item availability updated.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )
