from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import run_mutation

from .panel_index_service import item_for_panel
from .utils import panel_label


def mark_task_read(controller, task_id: str) -> dict[str, object]:
    return run_mutation(
        operation=lambda: controller._collaboration_workspace_presenter.mark_task_mentions_read(
            task_id
        ),
        success_message="Task mentions marked as read.",
        on_success=controller._request_domain_refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def mark_item_read(controller, panel_id: str, item_id: str) -> dict[str, object]:
    item = item_for_panel(controller, panel_id, item_id)
    task_id = str(item.get("state", {}).get("taskId") or "").strip() if item else ""
    if not task_id:
        return {
            "ok": False,
            "message": "The selected collaboration item is not linked to a task mention.",
        }
    return mark_task_read(controller, task_id)


def approve_request(controller, request_id: str) -> dict[str, object]:
    return run_mutation(
        operation=lambda: controller._collaboration_workspace_presenter.approve_request(
            request_id
        ),
        success_message="Approval request approved.",
        on_success=controller._request_domain_refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def reject_request(controller, request_id: str) -> dict[str, object]:
    return run_mutation(
        operation=lambda: controller._collaboration_workspace_presenter.reject_request(
            request_id
        ),
        success_message="Approval request rejected.",
        on_success=controller._request_domain_refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def export_panel(controller, panel_id: str) -> dict[str, object]:
    label = panel_label(str(panel_id or ""))
    message = (
        f"Export is not available here. Open the Reports section to generate "
        f"{label.lower()} summaries and collaboration exports."
    )
    controller._set_error_message("")
    controller._set_feedback_message(message)
    return {"ok": True, "message": message}


__all__ = [
    "approve_request",
    "export_panel",
    "mark_item_read",
    "mark_task_read",
    "reject_request",
]
