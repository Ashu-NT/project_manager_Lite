"""Transport-neutral application response."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class RegisterEntryResponseDto:
    id: str
    project_id: str
    project_name: str
    code: str
    entry_type: str
    title: str
    description: str
    severity: str
    status: str
    owner_name: str | None
    due_date: date | None
    impact_summary: str
    response_plan: str
    is_overdue: bool
    version: int


@dataclass(frozen=True)
class RegisterCatalogResponseDto:
    items: tuple[RegisterEntryResponseDto, ...]
    urgent_items: tuple[RegisterEntryResponseDto, ...]
    filtered_total: int
    scope_total: int
    scope_risk_total: int
    open_risks: int
    open_issues: int
    pending_changes: int
    active: int
    critical: int
    overdue: int
    due_soon: int
    page: int
    page_size: int
    sort_key: str
    sort_direction: str
