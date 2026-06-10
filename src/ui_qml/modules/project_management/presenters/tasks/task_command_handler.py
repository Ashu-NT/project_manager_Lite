from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    TaskBulkStatusCommand,
    TaskCreateCommand,
    TaskProgressCommand,
    TaskUpdateCommand,
)

from .validation import (
    coerce_string_list,
    optional_date,
    optional_float,
    optional_int,
    optional_text,
    require_text,
)


def suggest_code(desktop_api, payload: dict[str, Any]) -> str:
    from src.core.platform.common.code_generation import CodeGenerator

    project_id = optional_text(payload, "projectId")
    existing = {
        str(getattr(row, "code", "") or "").upper()
        for row in (desktop_api.list_tasks(project_id) if project_id else [])
    }
    name = optional_text(payload, "name")
    return CodeGenerator().generate(
        "task",
        exists=lambda code: code.upper() in existing,
        name=name or None,
        use_year=not bool(name),
    )


def create_task(desktop_api, payload: dict[str, Any]) -> None:
    command = TaskCreateCommand(
        project_id=require_text(
            payload, "projectId", "Select a project before creating a task."
        ),
        name=require_text(payload, "name", "Task name is required."),
        code=optional_text(payload, "taskCode"),
        description=optional_text(payload, "description") or "",
        start_date=optional_date(payload, "startDate"),
        duration_days=optional_int(payload, "durationDays"),
        status=optional_text(payload, "status") or "TODO",
        priority=optional_int(payload, "priority"),
        deadline=optional_date(payload, "deadline"),
    )
    desktop_api.create_task(command)


def update_task(desktop_api, payload: dict[str, Any]) -> None:
    command = TaskUpdateCommand(
        task_id=require_text(payload, "taskId", "Task ID is required for updates."),
        name=require_text(payload, "name", "Task name is required."),
        code=optional_text(payload, "taskCode"),
        description=optional_text(payload, "description") or "",
        start_date=optional_date(payload, "startDate"),
        duration_days=optional_int(payload, "durationDays"),
        status=optional_text(payload, "status") or "TODO",
        priority=optional_int(payload, "priority"),
        deadline=optional_date(payload, "deadline"),
        expected_version=optional_int(payload, "expectedVersion"),
    )
    desktop_api.update_task(command)


def update_progress(desktop_api, payload: dict[str, Any]) -> None:
    command = TaskProgressCommand(
        task_id=require_text(
            payload, "taskId", "Task ID is required for progress updates."
        ),
        percent_complete=optional_float(payload, "percentComplete"),
        actual_start=optional_date(payload, "actualStart"),
        actual_end=optional_date(payload, "actualEnd"),
        status=optional_text(payload, "status"),
        expected_version=optional_int(payload, "expectedVersion"),
    )
    desktop_api.update_progress(command)


def apply_bulk_status(desktop_api, payload: dict[str, Any]) -> None:
    task_ids = tuple(coerce_string_list(payload.get("taskIds")))
    if not task_ids:
        raise ValueError("Select one or more tasks first.")
    target_status = require_text(payload, "status", "Choose a valid target status.")
    reopen_percent_complete = None
    if str(target_status or "").strip().upper() == "IN_PROGRESS":
        reopen_percent_complete = optional_float(payload, "reopenPercentComplete")
    changed_tasks = desktop_api.apply_bulk_status(
        TaskBulkStatusCommand(
            task_ids=task_ids,
            status=target_status,
            reopen_percent_complete=reopen_percent_complete,
        )
    )
    if not changed_tasks:
        raise ValueError("Selected tasks already have this status.")


def bulk_delete_tasks(desktop_api, task_ids: Any) -> None:
    normalized_ids = tuple(coerce_string_list(task_ids))
    if not normalized_ids:
        raise ValueError("Select one or more tasks first.")
    deleted_ids = desktop_api.delete_tasks(normalized_ids)
    if not deleted_ids:
        raise ValueError("No selected tasks could be deleted.")
