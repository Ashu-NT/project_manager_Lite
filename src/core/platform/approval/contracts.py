from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.platform.approval.domain import ApprovalRequest, ApprovalStatus


class ApprovalRepository(ABC):
    @abstractmethod
    def add(self, request: ApprovalRequest) -> None: ...

    @abstractmethod
    def update(self, request: ApprovalRequest) -> None: ...

    @abstractmethod
    def get(self, request_id: str) -> ApprovalRequest | None: ...

    @abstractmethod
    def list_by_status(
        self,
        status: ApprovalStatus | None = None,
        *,
        limit: int = 200,
        project_id: str | None = None,
        entity_type: str | list[str] | None = None,
        entity_id: str | None = None,
    ) -> list[ApprovalRequest]: ...


__all__ = ["ApprovalRepository"]
