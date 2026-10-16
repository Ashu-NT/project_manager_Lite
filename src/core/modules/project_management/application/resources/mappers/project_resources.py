from __future__ import annotations

from src.core.modules.project_management.application.resources.dto.responses.project_resources import (
    ProjectResourceResponse,
)
from src.core.modules.project_management.domain.projects.project import ProjectResource


def map_project_resource(value: ProjectResource) -> ProjectResourceResponse:
    return ProjectResourceResponse(
        id=value.id,
        project_id=value.project_id,
        resource_id=value.resource_id,
        hourly_rate=value.hourly_rate,
        currency_code=value.currency_code,
        planned_hours=value.planned_hours,
        is_active=value.is_active,
        version=value.version,
    )


