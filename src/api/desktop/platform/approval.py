from __future__ import annotations

from src.api.desktop.platform._approval_labels import (
    approval_context_label,
    approval_display_label,
    approval_module_label,
)
from src.api.desktop.platform._support import execute_desktop_operation
from src.api.desktop.platform.models import (
    ApprovalDecisionCommand,
    ApprovalRequestDto,
    DesktopApiResult,
)
from src.core.platform.approval import ApprovalService
from src.core.platform.approval.domain import ApprovalRequest, ApprovalStatus


class PlatformApprovalDesktopApi:
    """Desktop-facing adapter for governed approval queue flows."""

    def __init__(self, *, approval_service: ApprovalService) -> None:
        self._approval_service = approval_service

    def list_requests(
        self,
        *,
        status: ApprovalStatus | str | None = None,
        entity_type: str | list[str] | None = None,
        limit: int = 500,
    ) -> DesktopApiResult[tuple[ApprovalRequestDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                self._serialize_request(request)
                for request in self._approval_service.list_requests(
                    status=status,
                    limit=limit,
                    entity_type=entity_type,
                )
            )
        )

    def approve_and_apply(
        self,
        command: ApprovalDecisionCommand,
    ) -> DesktopApiResult[ApprovalRequestDto]:
        return execute_desktop_operation(
            lambda: self._serialize_request(
                self._approval_service.approve_and_apply(command.request_id, note=command.note)
            )
        )

    def reject(self, command: ApprovalDecisionCommand) -> DesktopApiResult[ApprovalRequestDto]:
        return execute_desktop_operation(
            lambda: self._serialize_request(
                self._approval_service.reject(command.request_id, note=command.note)
            )
        )

    @staticmethod
    def _serialize_request(request: ApprovalRequest) -> ApprovalRequestDto:
        return ApprovalRequestDto(
            id=request.id,
            request_type=request.request_type,
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            project_id=request.project_id,
            payload=dict(request.payload or {}),
            status=request.status,
            requested_by_user_id=request.requested_by_user_id,
            requested_by_username=request.requested_by_username,
            requested_at=request.requested_at,
            decided_by_user_id=request.decided_by_user_id,
            decided_by_username=request.decided_by_username,
            decided_at=request.decided_at,
            decision_note=request.decision_note,
            module_label=approval_module_label(request),
            context_label=approval_context_label(request),
            display_label=approval_display_label(request),
        )


__all__ = ["PlatformApprovalDesktopApi"]
