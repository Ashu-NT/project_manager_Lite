from __future__ import annotations

from src.ui_qml.modules.maintenance.controllers.common import run_mutation


def create_work_request(controller, payload: dict) -> dict:
    return run_mutation(
        operation=lambda: controller._work_requests_workspace_presenter.create_work_request(
            dict(payload)
        ),
        success_message="Work request created.",
        on_success=controller.refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def update_work_request(controller, payload: dict) -> dict:
    return run_mutation(
        operation=lambda: controller._work_requests_workspace_presenter.update_work_request(
            dict(payload)
        ),
        success_message="Work request updated.",
        on_success=controller.refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def set_work_request_status(
    controller,
    work_request_id: str,
    status: str,
    expected_version: int,
) -> dict:
    return run_mutation(
        operation=lambda: controller._work_requests_workspace_presenter.set_work_request_status(
            work_request_id,
            status=status,
            expected_version=expected_version,
        ),
        success_message="Work request status updated.",
        on_success=controller.refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )
