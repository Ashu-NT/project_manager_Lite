from __future__ import annotations

from src.core.platform.api.desktop.approval._approval_labels import (
    approval_context_label,
    approval_display_label,
    approval_module_label,
)
from src.core.platform.api.desktop.approval.models.approval import (
    ApprovalRequestDto,
)
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.support._support import execute_desktop_operation
from src.core.platform.application.approval.commands import ApprovalCommandHandler
from src.core.platform.application.approval.dto.commands.decisions import (
    ApprovalDecisionCommand,
)
from src.core.platform.application.approval.dto.responses.requests import (
    ApprovalRequestResponse,
)
from src.core.platform.application.approval.queries import ApprovalQueryHandler
from src.core.platform.domain.approval import ApprovalStatus


class PlatformApprovalDesktopApi:
    """Desktop-facing adapter for governed approval queue flows."""

    def __init__(self, *, approval_commands: ApprovalCommandHandler, approval_queries: ApprovalQueryHandler) -> None:
        self._approval_commands = approval_commands
        self._approval_queries = approval_queries

    def list_requests(
        self,
        *,
        status: ApprovalStatus | str | None = None,
        project_id: str | None = None,
        entity_type: str | list[str] | None = None,
        limit: int = 500,
    ) -> DesktopApiResult[tuple[ApprovalRequestDto, ...]]:
        return execute_desktop_operation(
            lambda: self._list_requests(
                status=status, project_id=project_id,
                entity_type=entity_type, limit=limit,
            )
        )

    def _list_requests(
        self, *, status: ApprovalStatus | str | None,
        project_id: str | None, entity_type: str | list[str] | None, limit: int,
    ) -> tuple[ApprovalRequestDto, ...]:
        requests = tuple(self._approval_queries.list_requests(
            status=status, project_id=project_id,
            limit=max(1, min(int(limit), 500)), entity_type=entity_type,
        ))
        return tuple(
            self._serialize_request(request)
            for request in requests
        )

    def approve_and_apply(
        self,
        command: ApprovalDecisionCommand,
    ) -> DesktopApiResult[ApprovalRequestDto]:
        return execute_desktop_operation(
            lambda: self._serialize_request(
                self._approval_commands.approve_and_apply(command)
            )
        )

    def reject(self, command: ApprovalDecisionCommand) -> DesktopApiResult[ApprovalRequestDto]:
        return execute_desktop_operation(
            lambda: self._serialize_request(
                self._approval_commands.reject(command)
            )
        )

    @staticmethod
    def _serialize_request(response: ApprovalRequestResponse) -> ApprovalRequestDto:
        return ApprovalRequestDto(
            id=response.id,
            request_type=response.request_type,
            entity_type=response.entity_type,
            entity_id=response.entity_id,
            project_id=response.project_id,
            payload=response.payload,
            status=response.status,
            requested_by_user_id=response.requested_by_user_id,
            requested_by_username=response.requested_by_username,
            requested_at=response.requested_at,
            decided_by_user_id=response.decided_by_user_id,
            decided_by_username=response.decided_by_username,
            decided_at=response.decided_at,
            decision_note=response.decision_note,
            can_decide=response.can_decide,
            module_label=approval_module_label(response),
            context_label=approval_context_label(response),
            display_label=approval_display_label(response),
        )


__all__ = ["PlatformApprovalDesktopApi"]
