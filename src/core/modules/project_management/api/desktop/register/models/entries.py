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


@dataclass(frozen=True)
class RegisterCatalogPageDesktopDto:
    items: tuple[RegisterEntryDesktopDto, ...] = ()
    urgent_items: tuple[RegisterEntryDesktopDto, ...] = ()
    filtered_total: int = 0
    scope_total: int = 0
    scope_risk_total: int = 0
    open_risks: int = 0
    open_issues: int = 0
    pending_changes: int = 0
    active: int = 0
    critical: int = 0
    overdue: int = 0
    due_soon: int = 0
    page: int = 1
    page_size: int = 25


__all__ = ["RegisterCatalogPageDesktopDto", "RegisterEntryDesktopDto"]
