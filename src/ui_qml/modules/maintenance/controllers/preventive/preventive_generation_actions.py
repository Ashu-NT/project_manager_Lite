from __future__ import annotations

from .preventive_helpers import normalize_id


def regenerate_plan_schedule(controller, plan_id: str) -> dict:
    normalized = normalize_id(plan_id)
    if not normalized:
        return {"ok": False, "message": "Select a preventive plan first."}
    controller._set_is_busy(True)
    controller._set_error_message("")
    try:
        controller._preventive_workspace_presenter.regenerate_plan_schedule(
            plan_id=normalized
        )
        controller._latest_generation_results = []
        controller.refresh()
        controller._set_feedback_message("Preventive schedule regenerated.")
        return {"ok": True, "message": "Preventive schedule regenerated."}
    except Exception as exc:
        controller._set_feedback_message("")
        controller._set_error_message(str(exc))
        return {"ok": False, "message": str(exc)}
    finally:
        controller._set_is_busy(False)


def generate_due_work(controller, plan_id: str) -> dict:
    normalized = normalize_id(plan_id)
    if not normalized:
        return {"ok": False, "message": "Select a preventive plan first."}
    controller._set_is_busy(True)
    controller._set_error_message("")
    try:
        controller._latest_generation_results = (
            controller._preventive_workspace_presenter.generate_due_work(
                plan_id=normalized
            )
        )
        controller.refresh()
        controller._set_feedback_message("Due work generated.")
        return {"ok": True, "message": "Due work generated."}
    except Exception as exc:
        controller._set_feedback_message("")
        controller._set_error_message(str(exc))
        return {"ok": False, "message": str(exc)}
    finally:
        controller._set_is_busy(False)
