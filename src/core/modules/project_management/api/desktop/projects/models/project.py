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
    planned_budget: float | None
    planned_budget_label: str
    currency: str | None
    organization_id: str | None
    site_id: str | None
    site_label: str
    client_party_id: str | None
    manager_user_id: str | None
    version: int


__all__ = ["ProjectDesktopDto", "ProjectStatusDescriptor"]
