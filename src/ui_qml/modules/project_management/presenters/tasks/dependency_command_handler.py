from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    TaskDependencyCreateCommand,
    TaskDependencyUpdateCommand,
)

from .validation import optional_int, optional_text, require_text

def _empty_dependency_preview() -> dict[str, object]:
    return {
        "available": False,
        "isValid": True,
        "code": "",
        "summary": "",
        "detail": "",
        "riskLevel": "unknown",
        "affectedTaskCount": 0,
        "largestShiftDays": 0,
        "rows": [],
        "suggestions": [],
    }

def _serialize_dependency_preview(dto) -> dict[str, object]:
    if dto is None:
        return _empty_dependency_preview()
    return {
        "available": True,
        "isValid": dto.is_valid,
        "code": dto.code,
        "summary": dto.summary,
        "detail": dto.detail,
        "riskLevel": dto.risk_level,
        "affectedTaskCount": dto.affected_task_count,
        "largestShiftDays": dto.largest_shift_days,
        "rows": [
            {
                "taskId": row.task_id,
                "taskName": row.task_name,
                "beforeStartLabel": row.before_start_label,
                "beforeFinishLabel": row.before_finish_label,
                "afterStartLabel": row.after_start_label,
                "afterFinishLabel": row.after_finish_label,
                "startShiftDays": row.start_shift_days,
                "finishShiftDays": row.finish_shift_days,
            }
            for row in dto.rows
        ],
        "suggestions": list(dto.suggestions),
    }

def preview_create_dependency(desktop_api, payload: dict[str, Any]) -> dict[str, object]:
    task_id = str(payload.get("taskId") or "").strip()
    linked_task_id = str(payload.get("linkedTaskId") or "").strip()
    relationship_direction = str(payload.get("relationshipDirection") or "").strip()
    if not task_id or not linked_task_id or not relationship_direction:
        return _empty_dependency_preview()
    command = TaskDependencyCreateCommand(
        task_id=task_id,
        linked_task_id=linked_task_id,
        relationship_direction=relationship_direction,
        dependency_type=optional_text(payload, "dependencyType") or "FS",
        lag_days=optional_int(payload, "lagDays") or 0,
    )
    dto = desktop_api.preview_create_dependency(command)
    return _serialize_dependency_preview(dto)

def preview_update_dependency(desktop_api, payload: dict[str, Any]) -> dict[str, object]:
    dependency_id = str(payload.get("dependencyId") or "").strip()
    if not dependency_id:
        return _empty_dependency_preview()
    dependency_type = str(payload.get("dependencyType") or "FS").strip().upper()
    lag_days = int(payload.get("lagDays") or 0)
    dto = desktop_api.preview_update_dependency(
        TaskDependencyUpdateCommand(
            dependency_id=dependency_id,
            dependency_type=dependency_type,
            lag_days=lag_days,
        )
    )
    return _serialize_dependency_preview(dto)

def preview_delete_dependency(desktop_api, dependency_id: str) -> dict[str, object]:
    normalized_dependency_id = (dependency_id or "").strip()
    if not normalized_dependency_id:
        return _empty_dependency_preview()
    dto = desktop_api.preview_delete_dependency(normalized_dependency_id)
    return _serialize_dependency_preview(dto)

def create_dependency(desktop_api, payload: dict[str, Any]) -> None:
    command = TaskDependencyCreateCommand(
        task_id=require_text(
            payload, "taskId", "Select a task before creating a dependency."
        ),
        linked_task_id=require_text(
            payload, "linkedTaskId", "Select the linked task for this dependency."
        ),
        relationship_direction=require_text(
            payload,
            "relationshipDirection",
            "Select the dependency relationship direction.",
        ),
        dependency_type=optional_text(payload, "dependencyType") or "FS",
        lag_days=optional_int(payload, "lagDays") or 0,
    )
    desktop_api.create_dependency(command)

def update_dependency(desktop_api, payload: dict[str, Any]) -> None:
    dependency_id = (payload.get("dependencyId") or "").strip()
    if not dependency_id:
        raise ValueError("Dependency ID is required.")
    dependency_type = (payload.get("dependencyType") or "FS").strip().upper()
    lag_days = int(payload.get("lagDays") or 0)
    raw_version = payload.get("version")
    expected_version = (
        int(raw_version)
        if raw_version is not None and str(raw_version).strip() != ""
        else None
    )
    desktop_api.update_dependency(
        TaskDependencyUpdateCommand(
            dependency_id=dependency_id,
            dependency_type=dependency_type,
            lag_days=lag_days,
            expected_version=expected_version,
        )
    )

def delete_dependency(desktop_api, dependency_id: str) -> None:
    normalized_dependency_id = (dependency_id or "").strip()
    if not normalized_dependency_id:
        raise ValueError("Dependency ID is required to remove a dependency.")
    desktop_api.delete_dependency(normalized_dependency_id)
