"""Grouped command/query ports shared with approval consumers."""

from __future__ import annotations

from typing import Any, Protocol

from src.core.platform.contract.models.approval.contracts import (
    ApprovalDecisionInput,
)
from src.core.platform.domain.approval import ApprovalRequest, ApprovalStatus


class ApprovalCommands(Protocol):
    def request_change(
        self, *, request_type: str, entity_type: str, entity_id: str,
        project_id: str | None, module: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> ApprovalRequest: ...

    def approve_and_apply(self, command: ApprovalDecisionInput) -> ApprovalRequest: ...

    def reject(self, command: ApprovalDecisionInput) -> ApprovalRequest: ...


class ApprovalQueries(Protocol):
    def list_requests(
        self, *, status: ApprovalStatus | str | None = None,
        project_id: str | None = None, entity_type: str | list[str] | None = None,
        limit: int = 200,
    ) -> list[ApprovalRequest]: ...

    def eligible_request_ids(self, requests: tuple[ApprovalRequest, ...]) -> frozenset[str]: ...

    def list_pending(self, *, project_id: str | None = None, limit: int = 200) -> list[ApprovalRequest]: ...

    def count_pending(self, *, project_id: str | None = None) -> int: ...

    def list_recent(self, *, project_id: str | None = None, limit: int = 200) -> list[ApprovalRequest]: ...
