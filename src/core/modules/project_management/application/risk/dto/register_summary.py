from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from src.core.modules.project_management.domain.risk.register import (
    RegisterEntry,
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


@dataclass(frozen=True, slots=True)
class RegisterHighRiskItem:
    """Immutable scalar fact for an active high/critical register risk."""

    id: str
    project_id: str
    title: str
    severity: RegisterEntrySeverity
    status: RegisterEntryStatus
    owner_name: str | None
    due_date: date | None
    response_plan: str
    impact_summary: str
    description: str

    @classmethod
    def from_entry(cls, entry: RegisterEntry) -> RegisterHighRiskItem:
        return cls(
            id=entry.id,
            project_id=entry.project_id,
            title=entry.title,
            severity=entry.severity,
            status=entry.status,
            owner_name=entry.owner_name,
            due_date=entry.due_date,
            response_plan=entry.response_plan,
            impact_summary=entry.impact_summary,
            description=entry.description,
        )


@dataclass(frozen=True)
class RegisterDashboardSnapshot:
    summary: RegisterProjectSummary
    high_risks: tuple[RegisterHighRiskItem, ...] = ()


__all__ = [
    "RegisterDashboardSnapshot",
    "RegisterHighRiskItem",
    "RegisterProjectSummary",
    "RegisterUrgentItem",
]
