from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.controllers.common import run_mutation


def create_requisition(ctrl, payload: dict[str, object]) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._procurement_workspace_presenter.create_requisition(
            dict(payload)
        ),
        success_message="Requisition created.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )


def update_requisition(ctrl, payload: dict[str, object]) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._procurement_workspace_presenter.update_requisition(
            dict(payload)
        ),
        success_message="Requisition updated.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )


def add_requisition_line(ctrl, payload: dict[str, object]) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._procurement_workspace_presenter.add_requisition_line(
            dict(payload)
        ),
        success_message="Requisition line added.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )


def submit_requisition(ctrl, requisition_id: str) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._procurement_workspace_presenter.submit_requisition(
            requisition_id
        ),
        success_message="Requisition submitted.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )


def cancel_requisition(ctrl, requisition_id: str) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._procurement_workspace_presenter.cancel_requisition(
            requisition_id
        ),
        success_message="Requisition cancelled.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )
