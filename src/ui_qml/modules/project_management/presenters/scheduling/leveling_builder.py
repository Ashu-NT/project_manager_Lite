from __future__ import annotations

from datetime import date

from src.core.modules.project_management.api.desktop import (
    ProjectManagementSchedulingDesktopApi,
)
from src.core.modules.project_management.application.scheduling.models.leveling import (
    ProposedTaskMove,
    UnresolvedConflict,
)


def _date_label(value: date | None) -> str:
    return value.strftime("%b %d, %Y") if value else "--"


def _status_label(move: ProposedTaskMove) -> str:
    if move.infeasible_after:
        return "Infeasible"
    if move.deadline_warning:
        return "Deadline Risk"
    if move.critical_after:
        return "Critical"
    return "Resolved"


def _move_row(move: ProposedTaskMove) -> dict[str, object]:
    old_start_label = _date_label(move.old_start)
    new_start_label = _date_label(move.new_start)
    return {
        "id": move.task_id,
        "taskId": move.task_id,
        "taskName": move.task_name,
        "wbsCode": move.wbs_code,
        "oldStartLabel": old_start_label,
        "newStartLabel": new_start_label,
        "newFinishLabel": _date_label(move.new_finish),
        "shiftLabel": f"{old_start_label} -> {new_start_label} (+{move.shift_working_days}d)",
        "shiftWorkingDays": move.shift_working_days,
        "resourcesLabel": ", ".join(move.resource_names) if move.resource_names else "--",
        "reason": move.reason,
        "floatBefore": move.float_before,
        "floatAfter": move.float_after,
        "criticalBefore": move.critical_before,
        "criticalAfter": move.critical_after,
        "infeasibleAfter": move.infeasible_after,
        "deadlineWarning": move.deadline_warning,
        "statusLabel": _status_label(move),
    }


def _unresolved_row(conflict: UnresolvedConflict) -> dict[str, object]:
    return {
        "id": conflict.resource_id,
        "resourceId": conflict.resource_id,
        "resourceName": conflict.resource_name,
        "conflictDateLabel": _date_label(conflict.conflict_date),
        "totalAllocationLabel": f"{conflict.total_allocation_percent:.0f}%",
        "reason": conflict.reason,
    }


def build_resource_leveling_state(
    desktop_api: ProjectManagementSchedulingDesktopApi,
    project_id: str,
) -> dict[str, object]:
    normalized_id = (project_id or "").strip()
    if not normalized_id:
        return {
            "projectId": "",
            "scheduleFingerprint": "",
            "hasPreview": False,
            "isFeasible": True,
            "resourceConflictsBefore": 0,
            "resourceConflictsAfter": 0,
            "projectFinishBeforeLabel": "--",
            "projectFinishAfterLabel": "--",
            "criticalPathChanged": False,
            "warnings": [],
            "unresolvedConflicts": [],
            "moves": [],
            "emptyState": "Select a project to preview resource leveling.",
        }

    dto = desktop_api.preview_resource_leveling(normalized_id)
    moves = [_move_row(move) for move in dto.moves]
    unresolved = [_unresolved_row(conflict) for conflict in dto.unresolved_conflicts]
    empty_state = ""
    if not moves and not unresolved:
        empty_state = "No resource capacity conflicts were found -- nothing to level."
    return {
        "projectId": dto.project_id,
        "scheduleFingerprint": dto.schedule_fingerprint,
        "hasPreview": True,
        "isFeasible": dto.is_feasible,
        "resourceConflictsBefore": dto.resource_conflicts_before,
        "resourceConflictsAfter": dto.resource_conflicts_after,
        "projectFinishBeforeLabel": _date_label(dto.project_finish_before),
        "projectFinishAfterLabel": _date_label(dto.project_finish_after),
        "criticalPathChanged": dto.critical_path_changed,
        "warnings": list(dto.warnings),
        "unresolvedConflicts": unresolved,
        "moves": moves,
        "emptyState": empty_state,
    }


__all__ = ["build_resource_leveling_state"]
