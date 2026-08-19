from __future__ import annotations

import logging

from .formatting import shift_days_label

logger = logging.getLogger(__name__)

_SCHEDULE_STATUS_INFEASIBLE = "Infeasible"
_SCHEDULE_STATUS_CRITICAL = "Critical"
_SCHEDULE_STATUS_FLEXIBLE = "Flexible"


def _schedule_status_label(*, is_infeasible: bool, is_critical: bool) -> str:
    if is_infeasible:
        return _SCHEDULE_STATUS_INFEASIBLE
    if is_critical:
        return _SCHEDULE_STATUS_CRITICAL
    return _SCHEDULE_STATUS_FLEXIBLE


def _resolve_project_id(desktop_api, *, task_id: str, project_id: str) -> str:
    """The controller's project_id is the workspace-level project FILTER,
    which is legitimately blank when viewing "All Projects" -- not the
    selected task's own project. Falls back to the task's actual
    project_id via desktop_api.get_task, mirroring task_lookup.py's
    resolve_selected_task fallback used by the Dependencies section."""
    if project_id:
        return project_id
    try:
        task = desktop_api.get_task(task_id)
    except Exception:
        return ""
    return str(getattr(task, "project_id", "") or "") if task is not None else ""

_EMPTY_OVERVIEW = {
    "isAvailable": False,
    "taskId": "",
    "unavailableReason": "",
    "currentStartLabel": "--",
    "currentFinishLabel": "--",
    "isCritical": False,
    "isInfeasible": False,
    "scheduleStatusLabel": "",
    "totalFloatDays": None,
    "freeFloatDays": None,
    "baselineFinishLabel": "--",
    "scheduleVarianceDays": None,
    "scheduleVarianceLabel": "",
    "drivers": [],
    "conflicts": [],
    "actualVariances": [],
    "downstream": {
        "directSuccessorCount": 0,
        "downstreamTaskCount": 0,
        "downstreamMilestoneCount": 0,
        "criticalDownstreamCount": 0,
    },
}


def build_task_schedule_overview_state(
    desktop_api,
    *,
    task_id: str,
    project_id: str | None = None,
) -> dict[str, object]:
    """Task Detail -> Schedule Impact's always-visible current-state
    facts. Auto-loaded on task selection -- cheap (one CPM pass, no
    hypothetical), never a simulation (see build_task_schedule_impact_preview_state)."""
    normalized_task_id = (task_id or "").strip()
    normalized_project_id = _resolve_project_id(
        desktop_api, task_id=normalized_task_id, project_id=(project_id or "").strip()
    )
    if not normalized_task_id or not normalized_project_id:
        return dict(_EMPTY_OVERVIEW)
    try:
        dto = desktop_api.get_task_schedule_overview(normalized_task_id, normalized_project_id)
    except Exception:
        return dict(_EMPTY_OVERVIEW)
    if not dto.is_available:
        state = dict(_EMPTY_OVERVIEW)
        state["taskId"] = normalized_task_id
        state["unavailableReason"] = dto.unavailable_reason
        return state
    return {
        "isAvailable": True,
        "unavailableReason": "",
        "taskId": dto.task_id,
        "currentStartLabel": dto.current_start_label,
        "currentFinishLabel": dto.current_finish_label,
        "isCritical": dto.is_critical,
        "isInfeasible": dto.is_infeasible,
        "scheduleStatusLabel": _schedule_status_label(
            is_infeasible=dto.is_infeasible, is_critical=dto.is_critical
        ),
        "totalFloatDays": dto.total_float_days,
        "freeFloatDays": dto.free_float_days,
        "baselineFinishLabel": dto.baseline_finish_label,
        "scheduleVarianceDays": dto.schedule_variance_days,
        "scheduleVarianceLabel": (
            shift_days_label(dto.schedule_variance_days)
            if dto.schedule_variance_days is not None
            else ""
        ),
        "drivers": [
            {"kind": d.kind, "label": d.label, "detail": d.detail} for d in dto.drivers
        ],
        "conflicts": [
            {
                "taskId": c.task_id,
                "taskName": c.task_name,
                "constraintTypeLabel": c.constraint_type_label,
                "constraintDateLabel": c.constraint_date.isoformat(),
                "dependencyRequiredDateLabel": c.dependency_required_date.isoformat(),
                "direction": c.direction,
                "differenceWorkingDays": c.difference_working_days,
            }
            for c in dto.conflicts
        ],
        "actualVariances": [
            {
                "taskId": v.task_id,
                "taskName": v.task_name,
                "direction": v.direction,
                "actualDateLabel": v.actual_date.isoformat(),
                "dependencyRequiredDateLabel": v.dependency_required_date.isoformat(),
                "differenceWorkingDays": v.difference_working_days,
            }
            for v in dto.actual_variances
        ],
        "downstream": {
            "directSuccessorCount": dto.downstream.direct_successor_count,
            "downstreamTaskCount": dto.downstream.downstream_task_count,
            "downstreamMilestoneCount": dto.downstream.downstream_milestone_count,
            "criticalDownstreamCount": dto.downstream.critical_downstream_count,
        },
    }


_EMPTY_PREVIEW = {
    "isAvailable": False,
    "taskId": "",
    "delayWorkingDays": 0,
    "summary": "",
    "affectedCount": 0,
    "maxProjectFinishShiftDays": 0,
    "requiresApproval": False,
    "criticalPathChanged": False,
    "conflictCount": 0,
    "newlyCriticalCount": 0,
    "noLongerCriticalCount": 0,
    "blockedByDeadline": False,
    "blockedReason": "",
    "rows": [],
}


def build_task_schedule_impact_preview_state(
    desktop_api,
    *,
    task_id: str,
    project_id: str | None,
    delay_working_days: int,
) -> dict[str, object]:
    """Task Detail -> Schedule Impact's explicit "Preview Impact" what-if
    (§12/§13) -- run ONLY when the user asks for it. Never persists
    anything; the same typed, non-persisting backend preview the
    dependency dialogs use, applied to a task-level date change instead
    of a dependency change."""
    normalized_task_id = (task_id or "").strip()
    normalized_project_id = _resolve_project_id(
        desktop_api, task_id=normalized_task_id, project_id=(project_id or "").strip()
    )
    if not normalized_task_id or not normalized_project_id:
        return dict(_EMPTY_PREVIEW)
    try:
        dto = desktop_api.preview_task_schedule_impact(
            normalized_task_id,
            normalized_project_id,
            delay_working_days=delay_working_days,
        )
    except Exception:
        logger.exception(
            "build_task_schedule_impact_preview_state failed task_id=%s project_id=%s delay_working_days=%s",
            normalized_task_id,
            normalized_project_id,
            delay_working_days,
        )
        return dict(_EMPTY_PREVIEW)
    if not dto.is_available:
        state = dict(_EMPTY_PREVIEW)
        state["taskId"] = normalized_task_id
        state["delayWorkingDays"] = delay_working_days
        return state
    project_shift = int(dto.max_project_finish_shift_days or 0)
    if project_shift > 0:
        shift_label = f"Project finish would slip by {project_shift} working day(s)."
    elif project_shift < 0:
        shift_label = f"Project finish would improve by {abs(project_shift)} working day(s)."
    else:
        shift_label = "Project finish would not change."
    blocked_by_deadline = bool(getattr(dto, "blocked_by_deadline", False))
    blocked_reason = str(getattr(dto, "blocked_reason", "") or "")
    summary = (
        blocked_reason
        if blocked_by_deadline
        else f"{dto.affected_count} task(s) affected. " + shift_label
    )
    return {
        "isAvailable": True,
        "taskId": dto.task_id,
        "delayWorkingDays": delay_working_days,
        "summary": summary,
        "affectedCount": dto.affected_count,
        "maxProjectFinishShiftDays": project_shift,
        "requiresApproval": dto.requires_approval,
        "criticalPathChanged": dto.critical_path_changed,
        "conflictCount": dto.conflict_count,
        "newlyCriticalCount": len(dto.newly_critical_task_ids),
        "noLongerCriticalCount": len(dto.no_longer_critical_task_ids),
        "blockedByDeadline": blocked_by_deadline,
        "blockedReason": blocked_reason,
        "rows": [
            {
                "taskId": row.task_id,
                "taskName": row.task_name,
                "currentStartLabel": row.original_start.isoformat() if row.original_start else "--",
                "currentFinishLabel": row.original_finish.isoformat() if row.original_finish else "--",
                "projectedStartLabel": row.proposed_start.isoformat() if row.proposed_start else "--",
                "projectedFinishLabel": row.proposed_finish.isoformat() if row.proposed_finish else "--",
                "startShiftDays": row.start_shift_days,
                "finishShiftDays": row.finish_shift_days,
                "startShiftLabel": shift_days_label(row.start_shift_days),
                "finishShiftLabel": shift_days_label(row.finish_shift_days),
                "isCritical": row.is_critical,
                "isMilestone": row.is_milestone,
                "isChanged": row.task_id == normalized_task_id,
            }
            for row in dto.affected_tasks
        ],
    }


__all__ = [
    "build_task_schedule_impact_preview_state",
    "build_task_schedule_overview_state",
]
