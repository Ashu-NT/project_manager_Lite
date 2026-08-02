from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.core.platform.approval.domain import ApprovalRequest, ApprovalStatus


@dataclass(frozen=True)
class ApprovalPostCommitEvent:
    signal_name: str
    payload: str


@dataclass(frozen=True)
class ApprovalHandlerResult:
    post_commit_events: tuple[ApprovalPostCommitEvent, ...] = ()


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

    @abstractmethod
    def list_by_status_for_organization(
        self,
        organization_id: str,
        status: ApprovalStatus | None = None,
        *,
        limit: int = 200,
        project_id: str | None = None,
        entity_type: str | list[str] | None = None,
        entity_id: str | None = None,
    ) -> list[ApprovalRequest]: ...

    @abstractmethod
    def project_belongs_to_organization(self, project_id: str, organization_id: str) -> bool: ...


__all__ = [
    "ApprovalHandlerResult",
    "ApprovalPostCommitEvent",
    "ApprovalRepository",
]
