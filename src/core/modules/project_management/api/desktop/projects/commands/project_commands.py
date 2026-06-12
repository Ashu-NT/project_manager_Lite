from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from src.core.modules.project_management.domain.enums import ProjectStatus


@dataclass(frozen=True)
class ProjectCreateCommand:
    name: str
    code: str = ""
    description: str = ""
    status: str = ProjectStatus.PLANNED.value
    client_name: str | None = None
    client_contact: str | None = None
    planned_budget: float | None = None
    currency: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    organization_id: str | None = None
    site_id: str | None = None
    client_party_id: str | None = None
    manager_user_id: str | None = None


@dataclass(frozen=True)
class ProjectUpdateCommand:
    project_id: str
    name: str
    code: str = ""
    description: str = ""
    status: str = ProjectStatus.PLANNED.value
    client_name: str | None = None
    client_contact: str | None = None
    planned_budget: float | None = None
    currency: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    organization_id: str | None = None
    site_id: str | None = None
    client_party_id: str | None = None
    manager_user_id: str | None = None
    expected_version: int | None = None


__all__ = ["ProjectCreateCommand", "ProjectUpdateCommand"]
