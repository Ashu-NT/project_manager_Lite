from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class RegisterEntryDesktopDto:
    id: str
    project_id: str
    project_name: str
    code: str
    entry_type: str
    entry_type_label: str
    title: str
    description: str
    severity: str
    severity_label: str
    status: str
    status_label: str
    owner_name: str | None
    due_date: date | None
    due_date_label: str
    impact_summary: str
    response_plan: str
    is_overdue: bool
    version: int


__all__ = ["RegisterEntryDesktopDto"]
