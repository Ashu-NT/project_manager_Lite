from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum

from core.domain.identifiers import generate_id


class RegisterEntryType(str, Enum):
    RISK = "RISK"
    ISSUE = "ISSUE"
    CHANGE = "CHANGE"


class RegisterEntrySeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RegisterEntryStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    MITIGATED = "MITIGATED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CLOSED = "CLOSED"


@dataclass
class RegisterEntry:
    id: str
    project_id: str
    entry_type: RegisterEntryType
    title: str
    description: str = ""
    severity: RegisterEntrySeverity = RegisterEntrySeverity.MEDIUM
    status: RegisterEntryStatus = RegisterEntryStatus.OPEN
    owner_name: str | None = None
    due_date: date | None = None
    impact_summary: str = ""
    response_plan: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @staticmethod
    def create(
        project_id: str,
        *,
        entry_type: RegisterEntryType,
        title: str,
        description: str = "",
        severity: RegisterEntrySeverity = RegisterEntrySeverity.MEDIUM,
        status: RegisterEntryStatus = RegisterEntryStatus.OPEN,
        owner_name: str | None = None,
        due_date: date | None = None,
        impact_summary: str = "",
        response_plan: str = "",
    ) -> "RegisterEntry":
        now = datetime.now(timezone.utc)
        return RegisterEntry(
            id=generate_id(),
            project_id=project_id,
            entry_type=entry_type,
            title=title,
            description=description,
            severity=severity,
            status=status,
            owner_name=owner_name,
            due_date=due_date,
            impact_summary=impact_summary,
            response_plan=response_plan,
            created_at=now,
            updated_at=now,
        )


__all__ = [
    "RegisterEntry",
    "RegisterEntryType",
    "RegisterEntrySeverity",
    "RegisterEntryStatus",
]
