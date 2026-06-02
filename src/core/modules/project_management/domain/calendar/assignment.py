"""PM module calendar assignment domain models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from src.core.modules.project_management.domain.identifiers import generate_id


@dataclass
class ProjectCalendarAssignment:
    id: str
    project_id: str
    calendar_id: str
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    is_default: bool = False
    priority: int = 0

    @staticmethod
    def create(
        project_id: str,
        calendar_id: str,
        *,
        effective_from: Optional[date] = None,
        effective_to: Optional[date] = None,
        is_default: bool = False,
        priority: int = 0,
    ) -> "ProjectCalendarAssignment":
        return ProjectCalendarAssignment(
            id=generate_id(),
            project_id=project_id,
            calendar_id=calendar_id,
            effective_from=effective_from,
            effective_to=effective_to,
            is_default=is_default,
            priority=priority,
        )


@dataclass
class ResourceCalendarAssignment:
    id: str
    resource_id: str
    calendar_id: str
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    is_default: bool = False
    priority: int = 0

    @staticmethod
    def create(
        resource_id: str,
        calendar_id: str,
        *,
        effective_from: Optional[date] = None,
        effective_to: Optional[date] = None,
        is_default: bool = False,
        priority: int = 0,
    ) -> "ResourceCalendarAssignment":
        return ResourceCalendarAssignment(
            id=generate_id(),
            resource_id=resource_id,
            calendar_id=calendar_id,
            effective_from=effective_from,
            effective_to=effective_to,
            is_default=is_default,
            priority=priority,
        )


__all__ = ["ProjectCalendarAssignment", "ResourceCalendarAssignment"]
