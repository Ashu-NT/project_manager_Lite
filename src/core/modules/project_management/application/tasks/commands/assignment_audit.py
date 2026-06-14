from __future__ import annotations

from typing import Any

from src.core.shared.activity import record_activity


def record_assignment_action(
    owner: object,
    *,
    action: str,
    assignment_id: str,
    project_id: str,
    task_name: str,
    resource_name: str,
    extra: dict[str, Any] | None = None,
) -> None:
    details: dict[str, Any] = {
        "task_name": task_name,
        "resource_name": resource_name,
    }
    for key, value in (extra or {}).items():
        if value is not None:
            details[key] = value
    record_activity(
        owner,
        action=action,
        entity_type="task_assignment",
        entity_id=assignment_id,
        module="project_management",
        workspace_id=project_id,
        details=details,
    )


__all__ = ["record_assignment_action"]
