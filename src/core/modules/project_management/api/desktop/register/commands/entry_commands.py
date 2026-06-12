from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.core.modules.project_management.domain.risk.register import (
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)


@dataclass(frozen=True)
class RegisterEntryCreateCommand:
    project_id: str
    entry_type: str = RegisterEntryType.RISK.value
    title: str = ""
    description: str = ""
    severity: str = RegisterEntrySeverity.MEDIUM.value
    status: str = RegisterEntryStatus.OPEN.value
    owner_name: str | None = None
    due_date: date | None = None
    impact_summary: str = ""
    response_plan: str = ""
    code: str = ""


@dataclass(frozen=True)
class RegisterEntryUpdateCommand:
    entry_id: str
    project_id: str
    entry_type: str = RegisterEntryType.RISK.value
    title: str = ""
    description: str = ""
    severity: str = RegisterEntrySeverity.MEDIUM.value
    status: str = RegisterEntryStatus.OPEN.value
    owner_name: str | None = None
    due_date: date | None = None
    impact_summary: str = ""
    response_plan: str = ""
    expected_version: int | None = None
    code: str = ""


__all__ = ["RegisterEntryCreateCommand", "RegisterEntryUpdateCommand"]
