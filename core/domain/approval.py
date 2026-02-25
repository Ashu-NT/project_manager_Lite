from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from core.domain.identifiers import generate_id


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass
class ApprovalRequest:
    id: str
    request_type: str
    entity_type: str
    entity_id: str
    project_id: str | None
    payload: dict[str, Any]
    status: ApprovalStatus = ApprovalStatus.PENDING
    requested_by_user_id: str | None = None
    requested_by_username: str | None = None
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    decided_by_user_id: str | None = None
    decided_by_username: str | None = None
    decided_at: datetime | None = None
    decision_note: str | None = None

    @staticmethod
    def create(
        request_type: str,
        entity_type: str,
        entity_id: str,
        *,
        project_id: str | None,
        payload: dict[str, Any] | None = None,
        requested_by_user_id: str | None = None,
        requested_by_username: str | None = None,
    ) -> "ApprovalRequest":
        return ApprovalRequest(
            id=generate_id(),
            request_type=request_type,
            entity_type=entity_type,
            entity_id=entity_id,
            project_id=project_id,
            payload=payload or {},
            requested_by_user_id=requested_by_user_id,
            requested_by_username=requested_by_username,
        )


__all__ = ["ApprovalStatus", "ApprovalRequest"]

