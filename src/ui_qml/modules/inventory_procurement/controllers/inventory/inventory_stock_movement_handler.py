from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.controllers.common import run_mutation


def post_opening_balance(ctrl, payload: dict[str, object]) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._inventory_workspace_presenter.post_opening_balance(
            dict(payload)
        ),
        success_message="Opening balance posted.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )


def post_adjustment(ctrl, payload: dict[str, object]) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._inventory_workspace_presenter.post_adjustment(
            dict(payload)
        ),
        success_message="Adjustment posted.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )


def issue_stock(ctrl, payload: dict[str, object]) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._inventory_workspace_presenter.issue_stock(
            dict(payload)
        ),
        success_message="Stock issued.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )


def return_stock(ctrl, payload: dict[str, object]) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._inventory_workspace_presenter.return_stock(
            dict(payload)
        ),
        success_message="Stock returned.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )


def transfer_stock(ctrl, payload: dict[str, object]) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._inventory_workspace_presenter.transfer_stock(
            dict(payload)
        ),
        success_message="Stock transfer posted.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )
