from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.domain.risk.register import RegisterEntry


@dataclass(frozen=True, slots=True)
class RegisterCatalogReadItem:
    entry: RegisterEntry
    project_name: str = ""


@dataclass(frozen=True, slots=True)
class RegisterCatalogSummary:
    scope_total: int = 0
    scope_risk_total: int = 0
    open_risks: int = 0
    open_issues: int = 0
    pending_changes: int = 0
    active: int = 0
    critical: int = 0
    overdue: int = 0
    due_soon: int = 0


@dataclass(frozen=True, slots=True)
class RegisterCatalogReadPage:
    items: tuple[RegisterCatalogReadItem, ...] = ()
    urgent_items: tuple[RegisterCatalogReadItem, ...] = ()
    filtered_total: int = 0
    page: int = 1
    page_size: int = 25
    summary: RegisterCatalogSummary = RegisterCatalogSummary()


__all__ = [
    "RegisterCatalogReadItem",
    "RegisterCatalogReadPage",
    "RegisterCatalogSummary",
]
