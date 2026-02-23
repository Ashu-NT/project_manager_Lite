from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from core.domain.enums import ProjectStatus
from core.domain.identifiers import generate_id


@dataclass
class Project:
    id: str
    name: str
    description: str = ""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: ProjectStatus = ProjectStatus.PLANNED
    client_name: Optional[str] = None
    client_contact: Optional[str] = None
    planned_budget: Optional[float] = None
    currency: Optional[str] = None

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
    hourly_rate: Optional[float] = None
    currency_code: Optional[str] = None
    planned_hours: float = 0.0
    is_active: bool = True

    @staticmethod
    def create(
        project_id: str,
        resource_id: str,
        hourly_rate: Optional[float] = None,
        currency_code: Optional[str] = None,
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


__all__ = ["Project", "ProjectResource"]
