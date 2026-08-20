from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import run_mutation

from .row_builders import build_leveling_move_rows
from .scheduling_property_updates import set_leveling_move_rows, set_leveling_proposal
from .state import default_leveling_proposal


def preview_resource_leveling(controller) -> dict[str, object]:
    """Read-only compute -- mirrors load_variance_records_for_baseline's
    shape (is_loading, not is_busy; no activity-log entry, no domain
    refresh), since nothing is mutated until Apply is clicked."""
    project_id = controller._selected_project_id
    controller._set_is_loading(True)
    try:
        controller._set_error_message("")
        state = controller._scheduling_workspace_presenter.preview_resource_leveling(project_id)
    except Exception as exc:
        controller._set_error_message(str(exc))
        return {"ok": False, "message": str(exc)}
    finally:
        controller._set_is_loading(False)
    set_leveling_proposal(controller, state)
    set_leveling_move_rows(controller, build_leveling_move_rows(state))
    if state.get("moves"):
        message = f"{len(state['moves'])} proposed move(s) ready to review."
    else:
        message = state.get("emptyState", "Resource leveling preview ready.")
    controller._set_feedback_message(message)
    return {"ok": True, "message": message}


def apply_resource_leveling(controller) -> dict[str, object]:
    project_id = controller._selected_project_id
    move_count = len(controller._leveling_move_rows)

    def _on_success() -> None:
        controller._activity_log_svc.record(
            title="Resource leveling applied",
            status_label="Success",
            subtitle=project_id or "Current project",
            meta_text=f"{move_count} task(s) moved",
        )
        # The applied proposal is now historical fact, not a pending
        # preview -- consistent with the desktop API consuming its
        # cached proposal on Apply, force a fresh Preview before a
        # second Apply rather than silently re-showing stale moves.
        set_leveling_proposal(controller, default_leveling_proposal())
        set_leveling_move_rows(controller, [])
        controller.refresh()

    return run_mutation(
        operation=lambda: controller._scheduling_workspace_presenter.apply_resource_leveling(project_id),
        success_message="Resource leveling applied.",
        on_success=_on_success,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


__all__ = ["preview_resource_leveling", "apply_resource_leveling"]
