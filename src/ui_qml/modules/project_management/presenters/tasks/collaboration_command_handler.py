from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    TaskCollaborationPostCommand,
)

from .validation import coerce_string_list, require_text


def post_task_comment(collaboration_desktop_api, payload: dict[str, Any]) -> None:
    command = TaskCollaborationPostCommand(
        task_id=require_text(
            payload,
            "taskId",
            "Select a task before posting a collaboration update.",
        ),
        body=require_text(payload, "body", "Comment text is required."),
        attachments=tuple(coerce_string_list(payload.get("attachments"))),
        linked_document_ids=tuple(
            coerce_string_list(payload.get("linkedDocumentIds"))
        ),
    )
    collaboration_desktop_api.post_task_comment(command)


def mark_task_collaboration_read(collaboration_desktop_api, task_id: str) -> None:
    normalized_task_id = (task_id or "").strip()
    if not normalized_task_id:
        raise ValueError(
            "Select a task before marking collaboration updates as read."
        )
    collaboration_desktop_api.mark_task_mentions_read(normalized_task_id)


def touch_task_collaboration_presence(
    collaboration_desktop_api,
    task_id: str,
    *,
    activity: str = "reviewing",
) -> None:
    normalized_task_id = (task_id or "").strip()
    if not normalized_task_id:
        raise ValueError("Select a task before starting a presence session.")
    normalized_activity = (activity or "").strip() or "reviewing"
    collaboration_desktop_api.touch_task_presence(
        normalized_task_id,
        activity=normalized_activity,
    )


def clear_task_collaboration_presence(
    collaboration_desktop_api,
    task_id: str,
) -> None:
    normalized_task_id = (task_id or "").strip()
    if not normalized_task_id:
        return
    collaboration_desktop_api.clear_task_presence(normalized_task_id)
