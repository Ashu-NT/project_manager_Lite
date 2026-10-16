"""Grouped command/query ports shared with approval consumers."""

from __future__ import annotations

from typing import Any, Protocol

from src.core.platform.domain.approval import ApprovalRequest


class ApprovalCommands(Protocol):
    def request_change(
        self, *, request_type: str, entity_type: str, entity_id: str,
        project_id: str | None, module: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> ApprovalRequest: ...


class ApprovalQueries(Protocol):
    def list_pending(self, *, project_id: str | None = None, limit: int = 200) -> list[ApprovalRequest]: ...

    def count_pending(self, *, project_id: str | None = None) -> int: ...

    def list_recent(self, *, project_id: str | None = None, limit: int = 200) -> list[ApprovalRequest]: ...
