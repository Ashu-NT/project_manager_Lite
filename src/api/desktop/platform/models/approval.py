from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.core.platform.approval.domain import ApprovalStatus


@dataclass(frozen=True)
class ApprovalRequestDto:
    id: str
    request_type: str
    entity_type: str
    entity_id: str
    project_id: str | None
    payload: dict[str, Any] = field(default_factory=dict)
    status: ApprovalStatus = ApprovalStatus.PENDING
    requested_by_user_id: str | None = None
    requested_by_username: str | None = None
    requested_at: datetime | None = None
    decided_by_user_id: str | None = None
    decided_by_username: str | None = None
    decided_at: datetime | None = None
    decision_note: str | None = None
    module_label: str = ""
    context_label: str = ""
    display_label: str = ""


@dataclass(frozen=True)
class ApprovalDecisionCommand:
    request_id: str
    note: str | None = None
