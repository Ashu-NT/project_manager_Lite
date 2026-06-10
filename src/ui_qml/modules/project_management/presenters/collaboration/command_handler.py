from __future__ import annotations

from src.api.desktop.platform import ApprovalDecisionCommand, PlatformApprovalDesktopApi
from src.core.modules.project_management.api.desktop import (
    ProjectManagementCollaborationDesktopApi,
)


def mark_task_mentions_read(
    desktop_api: ProjectManagementCollaborationDesktopApi,
    task_id: str,
) -> None:
    desktop_api.mark_task_mentions_read(task_id)


def approve_request(
    approval_api: PlatformApprovalDesktopApi | None,
    request_id: str,
    *,
    note: str | None = None,
) -> None:
    if approval_api is None:
        raise RuntimeError("Platform approval API is not connected.")
    result = approval_api.approve_and_apply(
        ApprovalDecisionCommand(
            request_id=request_id,
            note=(note or "").strip() or None,
        )
    )
    if not result.ok:
        message = (
            result.error.message if result.error is not None else "Unable to approve the workflow item."
        )
        raise RuntimeError(message)


def reject_request(
    approval_api: PlatformApprovalDesktopApi | None,
    request_id: str,
    *,
    note: str | None = None,
) -> None:
    if approval_api is None:
        raise RuntimeError("Platform approval API is not connected.")
    result = approval_api.reject(
        ApprovalDecisionCommand(
            request_id=request_id,
            note=(note or "").strip() or None,
        )
    )
    if not result.ok:
        message = (
            result.error.message if result.error is not None else "Unable to reject the workflow item."
        )
        raise RuntimeError(message)
