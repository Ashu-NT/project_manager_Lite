from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.controllers.common import run_mutation


def create_reservation(ctrl, payload: dict[str, object]) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._reservations_workspace_presenter.create_reservation(
            dict(payload)
        ),
        success_message="Reservation created.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )


def issue_reservation(ctrl, payload: dict[str, object]) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._reservations_workspace_presenter.issue_reservation(
            dict(payload)
        ),
        success_message="Reserved stock issued.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )


def release_reservation(ctrl, reservation_id: str) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._reservations_workspace_presenter.release_reservation(
            reservation_id
        ),
        success_message="Reservation released.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )


def cancel_reservation(ctrl, reservation_id: str) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._reservations_workspace_presenter.cancel_reservation(
            reservation_id
        ),
        success_message="Reservation cancelled.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )
