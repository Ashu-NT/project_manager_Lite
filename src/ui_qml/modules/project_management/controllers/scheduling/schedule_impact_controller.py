from __future__ import annotations

from src.ui_qml.modules.project_management.presenters.tasks.schedule_impact_builder import (
    build_task_schedule_impact_preview_state,
)


def format_impact_tasks(tasks: list) -> list:
    result = []
    for t in tasks:
        is_critical = bool(t.get("isCritical") or t.get("is_critical"))
        shift_start = t.get("startShiftDays") or t.get("start_shift_days") or 0
        shift_finish = t.get("finishShiftDays") or t.get("finish_shift_days") or 0
        result.append({
            "id": t.get("taskId") or t.get("task_id") or "",
            "taskName": t.get("taskName") or t.get("task_name") or "",
            "startShiftDays": f"+{shift_start}d" if shift_start > 0 else f"{shift_start}d",
            "finishShiftDays": f"+{shift_finish}d" if shift_finish > 0 else f"{shift_finish}d",
            "isCritical": {
                "label": "Critical" if is_critical else "Normal",
                "tone": "danger" if is_critical else "default",
            },
        })
    return result


def compute_schedule_impact(
    presenter,
    payload: dict,
    fallback_task_id: str,
    fallback_project_id: str,
    *,
    delay_working_days: int = 1,
) -> tuple[dict[str, object] | None, bool, str]:
    """Returns (impact_dict, ok, error_message).

    Wired onto the same richer Schedule Impact serialization Task Detail's
    "Analyze Impact" trigger uses (FINAL PRODUCT DECISIONS decision 6) --
    a working-day-delay simulation via the shared ScheduleChangeImpactService
    (ProjectManagementSchedulingDesktopApi.preview_task_schedule_impact),
    not analyse_change_impact's narrower DTO. `delay_working_days` defaults
    to 1, matching Task Detail's own default/minimum (see
    TasksScheduleImpactSection.qml) since the Gantt Inspector's trigger has
    no delay-days input of its own.
    """
    task_id = str((payload or {}).get("taskId") or fallback_task_id or "")
    project_id = str((payload or {}).get("projectId") or fallback_project_id or "")
    if not task_id or not project_id:
        return None, False, "No activity or project selected."

    try:
        impact = build_task_schedule_impact_preview_state(
            presenter._desktop_api,
            task_id=task_id,
            project_id=project_id,
            delay_working_days=delay_working_days,
        )
    except Exception as exc:
        return None, False, str(exc)

    impact["available"] = bool(impact.get("isAvailable"))
    impact["affectedTasks"] = impact.get("rows", [])
    return impact, True, ""


__all__ = ["compute_schedule_impact", "format_impact_tasks"]
