from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    TaskDependencyCreateCommand,
    TaskDependencyUpdateCommand,
)

from .validation import optional_int, optional_text, require_text


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
    desktop_api.update_dependency(
        TaskDependencyUpdateCommand(
            dependency_id=dependency_id,
            dependency_type=dependency_type,
            lag_days=lag_days,
        )
    )


def delete_dependency(desktop_api, dependency_id: str) -> None:
    normalized_dependency_id = (dependency_id or "").strip()
    if not normalized_dependency_id:
        raise ValueError("Dependency ID is required to remove a dependency.")
    desktop_api.delete_dependency(normalized_dependency_id)
