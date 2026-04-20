from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from src.core.modules.project_management.domain.risk.register import (
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)


@dataclass
class RegisterUrgentItem:
    entry_id: str
    entry_type: RegisterEntryType
    title: str
    severity: RegisterEntrySeverity
    status: RegisterEntryStatus
    owner_name: str | None
    due_date: date | None


@dataclass
class RegisterProjectSummary:
    open_risks: int = 0
    open_issues: int = 0
    pending_changes: int = 0
    overdue_items: int = 0
    critical_items: int = 0
    urgent_items: list[RegisterUrgentItem] = field(default_factory=list)


__all__ = ["RegisterProjectSummary", "RegisterUrgentItem"]
