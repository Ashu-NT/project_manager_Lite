from __future__ import annotations

from src.core.modules.project_management.api.desktop import (
    ProjectManagementSchedulingDesktopApi,
)


def _status_label(move) -> str:
    if move.infeasible_after:
        return "Infeasible"
    if move.deadline_warning:
        return "Deadline Risk"
    if move.critical_after:
        return "Critical"
    return "Resolved"


def _move_row(move) -> dict[str, object]:
    return {
        "id": move.task_id,
        "taskId": move.task_id,
        "taskName": move.task_name,
        "wbsCode": move.wbs_code,
        "oldStartLabel": move.old_start_label,
        "newStartLabel": move.new_start_label,
        "newFinishLabel": move.new_finish_label,
        "shiftLabel": f"{move.old_start_label} -> {move.new_start_label} (+{move.shift_working_days}d)",
        "shiftWorkingDays": move.shift_working_days,
        "resourcesLabel": move.resource_names_label,
        "reason": move.reason,
        "floatBefore": move.float_before,
        "floatAfter": move.float_after,
        "criticalBefore": move.critical_before,
        "criticalAfter": move.critical_after,
        "infeasibleAfter": move.infeasible_after,
        "deadlineWarning": move.deadline_warning,
        "statusLabel": _status_label(move),
    }


def _unresolved_row(conflict) -> dict[str, object]:
    return {
        "id": conflict.resource_id,
        "resourceId": conflict.resource_id,
        "resourceName": conflict.resource_name,
        "conflictDateLabel": conflict.conflict_date_label,
        "totalAllocationLabel": conflict.total_allocation_label,
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
        "projectFinishBeforeLabel": dto.project_finish_before_label,
        "projectFinishAfterLabel": dto.project_finish_after_label,
        "criticalPathChanged": dto.critical_path_changed,
        "warnings": list(dto.warnings),
        "unresolvedConflicts": unresolved,
        "moves": moves,
        "emptyState": empty_state,
    }


__all__ = ["build_resource_leveling_state"]
