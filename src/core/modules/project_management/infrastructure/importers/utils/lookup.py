"""Entity lookup helpers shared across domain importers."""

from __future__ import annotations

from typing import Any


def build_project_lookup(project_service: Any) -> dict[str, Any]:
    """Build a dict keyed by both project.id and project.name.lower()."""
    lookup: dict[str, Any] = {}
    for project in project_service.list_projects():
        lookup[project.id] = project
        lookup[project.name.strip().lower()] = project
    return lookup


def resolve_project(
    lookup: dict[str, Any],
    *,
    project_id: str | None,
    project_name: str | None,
) -> Any | None:
    if project_id and project_id in lookup:
        return lookup[project_id]
    key = (project_name or "").strip().lower()
    return lookup.get(key) if key else None


__all__ = [
    "build_project_lookup",
    "resolve_project",
]
