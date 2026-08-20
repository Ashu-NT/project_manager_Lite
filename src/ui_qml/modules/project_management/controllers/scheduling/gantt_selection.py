"""Atomic Gantt selection projection with no repository or CPM access."""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.scheduling.models import GanttTaskRowDto

from .state import default_selected_activity


def set_gantt_selection(controller, task_id: str) -> None:
    normalized = str(task_id or "").strip()
    row = controller._gantt_model.row_for_task(normalized)
    if row is None or not controller._gantt_model.contains_filtered_task(normalized):
        normalized = ""
        detail = default_selected_activity()
    else:
        detail = _serialize_detail(
            row,
            dependency_count=len(controller._gantt_model.incident_edge_ids(normalized)),
        )
    if (
        normalized == controller._selected_activity_id
        and detail == controller._selected_activity
    ):
        return
    id_changed = normalized != controller._selected_activity_id
    detail_changed = detail != controller._selected_activity
    controller._selected_activity_id = normalized
    controller._selected_activity = detail
    # Both fields are assigned before either observer is notified.
    if id_changed:
        controller.selectedActivityIdChanged.emit()
    if detail_changed:
        controller.selectedActivityChanged.emit()


def _serialize_detail(row: GanttTaskRowDto, *, dependency_count: int) -> dict[str, object]:
    status_label = (
        "Infeasible"
        if row.is_infeasible
        else "Critical" if row.is_critical else row.status_label
    )
    return {
        "id": row.task_id,
        "taskId": row.task_id,
        "title": row.name,
        "statusLabel": status_label,
        "subtitle": f"{_date_label(row.start_date)} -> {_date_label(row.finish_date)}",
        "description": row.description or "Schedule activity selected for planning inspection.",
        "emptyState": "",
        "fields": [
            _field("Activity ID", row.task_id, "Authoritative task identifier."),
            _field("Activity code", row.code or "-", "Authoritative Task.code."),
            _field("WBS", row.wbs_code or "-", "Canonical work breakdown code."),
            _field("Start", _date_label(row.start_date), f"Latest {_date_label(row.latest_start)}"),
            _field("Finish", _date_label(row.finish_date), f"Latest {_date_label(row.latest_finish)}"),
            _field("Duration", _int_label(row.duration_days), f"Remaining {_int_label(row.remaining_duration_days)}"),
            _field("Float", _int_label(row.total_float_days), "Total float in working days."),
            _field("Deadline", _date_label(row.deadline), row.constraint_type_label or "No explicit constraint"),
            _field("Dependencies", str(dependency_count), "Project-wide incident dependency index."),
        ],
        "state": {
            "activityId": row.task_id,
            "taskId": row.task_id,
            "projectId": row.project_id,
            "activityCode": row.code,
            "wbsCode": row.wbs_code,
            "title": row.name,
            "description": row.description,
            "statusLabel": row.status_label,
            "startDateLabel": _date_label(row.start_date),
            "finishDateLabel": _date_label(row.finish_date),
            "durationLabel": _int_label(row.duration_days),
            "remainingDurationLabel": _int_label(row.remaining_duration_days),
            "floatLabel": _int_label(row.total_float_days),
            "deadlineLabel": _date_label(row.deadline),
            "progressPercent": row.percent_complete,
            "isMilestone": row.is_milestone,
            "isSummary": row.is_summary,
        },
    }


def _field(label: str, value: str, supporting_text: str) -> dict[str, str]:
    return {"label": label, "value": value, "supportingText": supporting_text}


def _date_label(value) -> str:
    return value.isoformat() if value is not None else "-"


def _int_label(value: int | None) -> str:
    return "-" if value is None else f"{int(value)}d"


__all__ = ["set_gantt_selection"]
