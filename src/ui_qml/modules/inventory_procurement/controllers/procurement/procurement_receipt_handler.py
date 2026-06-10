from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.controllers.common import run_mutation


def post_receipt(ctrl, payload: dict[str, object]) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._procurement_workspace_presenter.post_receipt(
            dict(payload)
        ),
        success_message="Receipt posted.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )
