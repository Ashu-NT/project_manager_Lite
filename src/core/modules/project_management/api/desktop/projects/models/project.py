from __future__ import annotations
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ProjectStatusDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class ProjectDesktopDto:
    id: str
    name: str
    code: str
    description: str
    status: str
    status_label: str
    start_date: date | None
    end_date: date | None
    client_name: str | None
    client_contact: str | None
    approved_budget: str | None
    approved_budget_label: str
    financial_currency_code: str
    organization_id: str | None
    site_id: str | None
    site_label: str
    client_party_id: str | None
    manager_user_id: str | None
    version: int
    client_label: str = ""


@dataclass(frozen=True)
class ProjectCatalogPageDesktopDto:
    items: tuple[ProjectDesktopDto, ...] = ()
    filtered_total: int = 0
    total: int = 0
    active: int = 0
    planned: int = 0
    on_hold: int = 0
    completed: int = 0
    page: int = 1
    page_size: int = 25
    sort_key: str = "title"
    sort_direction: str = "asc"


__all__ = ["ProjectCatalogPageDesktopDto", "ProjectDesktopDto", "ProjectStatusDescriptor"]
