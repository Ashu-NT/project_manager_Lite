from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import (
    serialize_scheduling_collection_view_model,
)

from .row_builders import build_baseline_variance_rows
from .schedule_impact_controller import compute_schedule_impact, format_impact_tasks
from .scheduling_property_updates import set_baseline_variance_rows, set_calculator_result


def calculate_working_days(controller, payload: dict) -> dict:
    controller._set_error_message("")
    try:
        result = controller._scheduling_workspace_presenter.calculate_working_days(dict(payload))
    except Exception as exc:
        set_calculator_result(controller, "")
        controller._set_feedback_message("")
        controller._set_error_message(str(exc))
        return {"ok": False, "message": str(exc)}
    set_calculator_result(controller, result)
    controller._set_feedback_message("")
    controller._activity_log_svc.record(
        title="Working-day calculation completed",
        status_label="Info",
        subtitle=result,
        meta_text=str(payload.get("startDate", "") or ""),
    )
    controller.refresh()
    return {"ok": True, "message": result}


def export_schedule(controller) -> dict:
    try:
        message = controller._scheduling_workspace_presenter.export_schedule(
            controller._selected_project_id
        )
    except Exception as exc:
        controller._set_error_message(str(exc))
        controller._set_feedback_message("")
        return {"ok": False, "message": str(exc)}
    controller._set_error_message("")
    controller._set_feedback_message(message)
    controller._activity_log_svc.record(
        title="Schedule export requested",
        status_label="Info",
        subtitle="Export adapter pending",
        meta_text=controller._selected_project_id or "Current project",
    )
    controller.refresh()
    return {"ok": True, "message": message}


def load_variance_records_for_baseline(controller, baseline_id: str) -> None:
    normalized_id = (baseline_id or "").strip()
    controller._set_is_loading(True)
    try:
        controller._set_error_message("")
        collection = controller._scheduling_workspace_presenter.build_baseline_variance_collection(
            normalized_id
        )
        serialized = serialize_scheduling_collection_view_model(collection)
        set_baseline_variance_rows(controller, build_baseline_variance_rows(serialized))
    except Exception as exc:
        controller._set_error_message(str(exc))
    finally:
        controller._set_is_loading(False)


def run_compute_schedule_impact(controller, payload: dict) -> dict:
    impact, ok, error = compute_schedule_impact(
        controller._scheduling_workspace_presenter,
        payload,
        controller._selected_activity_id,
        controller._selected_project_id,
    )
    if not ok:
        return {"ok": False, "message": error}
    if impact != controller._schedule_impact:
        controller._schedule_impact = impact
        controller._table_models.schedule_impact_tasks.set_rows(
            format_impact_tasks(impact.get("affectedTasks", []))
            if isinstance(impact, dict) else []
        )
        controller.scheduleImpactChanged.emit()
    return {"ok": True, "message": "Impact analysis complete."}


__all__ = [
    "calculate_working_days",
    "export_schedule",
    "load_variance_records_for_baseline",
    "run_compute_schedule_impact",
]
