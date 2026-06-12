from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.core.modules.project_management.domain.enums import ProjectStatus
from src.core.modules.project_management.domain.identifiers import generate_id


@dataclass
class Project:
    id: str
    name: str
    code: str = ""
    description: str = ""
    start_date: date | None = None
    end_date: date | None = None
    status: ProjectStatus = ProjectStatus.PLANNED
    client_name: str | None = None
    client_contact: str | None = None
    planned_budget: float | None = None
    currency: str | None = None
    organization_id: str | None = None
    site_id: str | None = None
    client_party_id: str | None = None
    manager_user_id: str | None = None
    version: int = 1

    @staticmethod
    def create(name: str, description: str = "", **extra) -> "Project":
        return Project(
            id=generate_id(),
            name=name,
            description=description,
            **extra,
        )


@dataclass
class ProjectResource:
    id: str
    project_id: str
    resource_id: str
    hourly_rate: float | None = None
    currency_code: str | None = None
    planned_hours: float = 0.0
    is_active: bool = True

    @staticmethod
    def create(
        project_id: str,
        resource_id: str,
        hourly_rate: float | None = None,
        currency_code: str | None = None,
        planned_hours: float = 0.0,
        is_active: bool = True,
    ) -> "ProjectResource":
        return ProjectResource(
            id=generate_id(),
            project_id=project_id,
            resource_id=resource_id,
            hourly_rate=hourly_rate,
            currency_code=currency_code,
            planned_hours=planned_hours,
            is_active=is_active,
        )
