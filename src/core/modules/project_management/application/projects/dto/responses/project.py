"""Transport-neutral project result, without desktop display formatting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.core.modules.project_management.domain.enums import ProjectStatus


@dataclass(frozen=True, slots=True)
class ProjectResponse:
    id: str
    name: str
    code: str
    description: str
    status: ProjectStatus
    start_date: date | None
    end_date: date | None
    client_name: str | None
    client_contact: str | None
    organization_id: str | None
    site_id: str | None
    department_id: str | None
    client_party_id: str | None
    manager_user_id: str | None
    version: int
    financial_currency_code: str
    approved_budget: Decimal | None
    approved_budget_currency: str
    approved_budget_visible: bool


