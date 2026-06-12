from __future__ import annotations

from .utils import parse_iso_date


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
) -> tuple[dict[str, object] | None, bool, str]:
    """Returns (impact_dict, ok, error_message)."""
    task_id = str((payload or {}).get("taskId") or fallback_task_id or "")
    project_id = str((payload or {}).get("projectId") or fallback_project_id or "")
    if not task_id or not project_id:
        return None, False, "No activity or project selected."

    proposed_start = parse_iso_date((payload or {}).get("proposedStart"))
    proposed_finish = parse_iso_date((payload or {}).get("proposedFinish"))
    raw_duration = (payload or {}).get("proposedDurationDays")
    proposed_duration_days = int(raw_duration) if raw_duration else None

    try:
        dto = presenter._desktop_api.analyse_change_impact(
            project_id=project_id,
            task_id=task_id,
            proposed_start=proposed_start,
            proposed_finish=proposed_finish,
            proposed_duration_days=proposed_duration_days,
        )
    except Exception as exc:
        return None, False, str(exc)

    if dto is None:
        impact: dict[str, object] = {
            "taskId": task_id,
            "affectedCount": 0,
            "maxProjectFinishShiftDays": 0,
            "requiresApproval": False,
            "newlyCriticalCount": 0,
            "noLongerCriticalCount": 0,
            "affectedTasks": [],
            "available": False,
        }
    else:
        impact = {
            "taskId": dto.task_id,
            "affectedCount": dto.affected_count,
            "maxProjectFinishShiftDays": dto.max_project_finish_shift_days,
            "requiresApproval": dto.requires_approval,
            "newlyCriticalCount": dto.newly_critical_count,
            "noLongerCriticalCount": dto.no_longer_critical_count,
            "affectedTasks": [
                {
                    "taskId": t.task_id,
                    "taskName": t.task_name,
                    "startShiftDays": t.start_shift_days,
                    "finishShiftDays": t.finish_shift_days,
                    "isCritical": t.is_critical,
                }
                for t in dto.affected_tasks
            ],
            "available": True,
        }
    return impact, True, ""


__all__ = ["compute_schedule_impact", "format_impact_tasks"]
