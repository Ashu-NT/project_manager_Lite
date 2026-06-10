from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.controllers.common import run_mutation


def create_location(ctrl, payload: dict[str, object]) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._inventory_workspace_presenter.create_location(
            dict(payload)
        ),
        success_message="Storage location created.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )


def update_location(ctrl, payload: dict[str, object]) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._inventory_workspace_presenter.update_location(
            dict(payload)
        ),
        success_message="Storage location updated.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )


def upsert_reorder_policy(ctrl, payload: dict[str, object]) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._inventory_workspace_presenter.upsert_reorder_policy(
            dict(payload)
        ),
        success_message="Reorder policy saved.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )


def schedule_cycle_count(ctrl, payload: dict[str, object]) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._inventory_workspace_presenter.schedule_cycle_count(
            dict(payload)
        ),
        success_message="Cycle count scheduled.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )


def complete_cycle_count(ctrl, payload: dict[str, object]) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._inventory_workspace_presenter.complete_cycle_count(
            dict(payload)
        ),
        success_message="Cycle count completed.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )
