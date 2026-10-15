from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApprovalDecisionCommand:
    request_id: str
    note: str | None = None
