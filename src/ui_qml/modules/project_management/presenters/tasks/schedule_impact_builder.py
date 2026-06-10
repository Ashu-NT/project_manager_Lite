from __future__ import annotations

from .formatting import shift_days_label


def build_schedule_impact_state(
    desktop_api,
    *,
    task_id: str,
    project_id: str | None = None,
) -> dict[str, object]:
    normalized_task_id = (task_id or "").strip()
    normalized_project_id = (project_id or "").strip()
    if not normalized_task_id or not normalized_project_id:
        return {
            "available": False,
            "taskId": normalized_task_id,
            "summary": "Select a task with a project to view schedule impact.",
            "rows": [],
            "affectedCount": 0,
            "maxProjectFinishShiftDays": 0,
            "requiresApproval": False,
            "approvalLabel": "",
            "newlyCriticalCount": 0,
            "noLongerCriticalCount": 0,
        }
    try:
        report = desktop_api.get_schedule_impact(
            normalized_task_id, normalized_project_id
        )
    except Exception:
        return {
            "available": False,
            "taskId": normalized_task_id,
            "summary": "Schedule impact analysis is unavailable.",
            "rows": [],
            "affectedCount": 0,
            "maxProjectFinishShiftDays": 0,
            "requiresApproval": False,
            "approvalLabel": "",
            "newlyCriticalCount": 0,
            "noLongerCriticalCount": 0,
        }
    if not report.is_available:
        return {
            "available": False,
            "taskId": normalized_task_id,
            "summary": (
                "Schedule impact analysis requires the task to have a start date "
                "and a connected scheduling service."
            ),
            "rows": [],
            "affectedCount": 0,
            "maxProjectFinishShiftDays": 0,
            "requiresApproval": False,
            "approvalLabel": "",
            "newlyCriticalCount": 0,
            "noLongerCriticalCount": 0,
        }
    project_shift = int(report.max_project_finish_shift_days or 0)
    if project_shift > 0:
        shift_label = f"Project finish would slip by {project_shift} working day(s)."
    elif project_shift < 0:
        shift_label = (
            f"Project finish would improve by {abs(project_shift)} working day(s)."
        )
    else:
        shift_label = "Project finish would not change."
    summary = (
        f"Simulating 1-day start slip: {report.affected_count} task(s) affected. "
        + shift_label
    )
    newly_critical = int(len(report.newly_critical_task_ids))
    no_longer_critical = int(len(report.no_longer_critical_task_ids))
    rows = [
        {
            "taskId": task.task_id,
            "taskName": task.task_name,
            "startShift": shift_days_label(task.start_shift_days),
            "finishShift": shift_days_label(task.finish_shift_days),
            "startShiftDays": task.start_shift_days,
            "finishShiftDays": task.finish_shift_days,
            "isCritical": task.is_critical,
            "criticalLabel": "Critical" if task.is_critical else "Non-critical",
            "isChanged": task.task_id == normalized_task_id,
        }
        for task in report.affected_tasks
    ]
    return {
        "available": True,
        "taskId": normalized_task_id,
        "summary": summary,
        "rows": rows,
        "affectedCount": report.affected_count,
        "maxProjectFinishShiftDays": project_shift,
        "requiresApproval": report.requires_approval,
        "approvalLabel": "Approval required" if report.requires_approval else "",
        "newlyCriticalCount": newly_critical,
        "noLongerCriticalCount": no_longer_critical,
    }
