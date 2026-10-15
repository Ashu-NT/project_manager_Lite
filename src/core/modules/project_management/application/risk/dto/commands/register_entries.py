from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.core.modules.project_management.application.risk._command_values import (
    REGISTER_UNSET,
)
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
    entry_type: str | None = None
    title: str | None = None
    description: str | None = None
    severity: str | None = None
    status: str | None = None
    owner_name: str | None = None
    due_date: date | None | object = REGISTER_UNSET
    impact_summary: str | None = None
    response_plan: str | None = None
    expected_version: int | None = None
    code: str | None = None


@dataclass(frozen=True)
class RegisterEntryDeleteCommand:
    entry_id: str


@dataclass(frozen=True)
class RegisterEntryBulkStatusCommand:
    entry_ids: tuple[str, ...]
    status: str
