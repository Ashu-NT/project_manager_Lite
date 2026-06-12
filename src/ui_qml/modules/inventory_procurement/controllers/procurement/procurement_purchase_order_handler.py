from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.controllers.common import run_mutation


def create_purchase_order(ctrl, payload: dict[str, object]) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._procurement_workspace_presenter.create_purchase_order(
            dict(payload)
        ),
        success_message="Purchase order created.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )


def update_purchase_order(ctrl, payload: dict[str, object]) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._procurement_workspace_presenter.update_purchase_order(
            dict(payload)
        ),
        success_message="Purchase order updated.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )


def add_purchase_order_line(ctrl, payload: dict[str, object]) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._procurement_workspace_presenter.add_purchase_order_line(
            dict(payload)
        ),
        success_message="Purchase-order line added.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )


def submit_purchase_order(ctrl, purchase_order_id: str) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._procurement_workspace_presenter.submit_purchase_order(
            purchase_order_id
        ),
        success_message="Purchase order submitted.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )


def send_purchase_order(ctrl, purchase_order_id: str) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._procurement_workspace_presenter.send_purchase_order(
            purchase_order_id
        ),
        success_message="Purchase order sent.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )


def cancel_purchase_order(ctrl, purchase_order_id: str) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._procurement_workspace_presenter.cancel_purchase_order(
            purchase_order_id
        ),
        success_message="Purchase order cancelled.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )


def close_purchase_order(ctrl, purchase_order_id: str) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._procurement_workspace_presenter.close_purchase_order(
            purchase_order_id
        ),
        success_message="Purchase order closed.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )
