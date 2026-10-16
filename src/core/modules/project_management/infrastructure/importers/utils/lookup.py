"""Entity lookup helpers shared across domain importers."""

from __future__ import annotations

from src.core.modules.project_management.application.projects.dto.responses.project import (
    ProjectResponse,
)
from src.core.modules.project_management.application.projects.queries.project_query import (
    ProjectQueryHandler,
)


def build_project_lookup(project_service: ProjectQueryHandler) -> dict[str, ProjectResponse]:
    """Build a dict keyed by both project.id and project.name.lower()."""
    lookup: dict[str, ProjectResponse] = {}
    for project in project_service.list_projects():
        lookup[project.id] = project
        lookup[project.name.strip().lower()] = project
    return lookup


def resolve_project(
    lookup: dict[str, ProjectResponse],
    *,
    project_id: str | None,
    project_name: str | None,
) -> ProjectResponse | None:
    if project_id and project_id in lookup:
        return lookup[project_id]
    key = (project_name or "").strip().lower()
    return lookup.get(key) if key else None


__all__ = [
    "build_project_lookup",
    "resolve_project",
]
