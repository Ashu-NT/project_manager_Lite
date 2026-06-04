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


def resolve_task(
    task_service: Any,
    *,
    project_id: str,
    task_id: str | None,
    task_name: str | None,
) -> Any | None:
    tasks = task_service.list_tasks_for_project(project_id)
    if task_id:
        found = next((t for t in tasks if t.id == task_id), None)
        if found is not None:
            return found
    if task_name:
        key = task_name.strip().lower()
        return next((t for t in tasks if t.name.strip().lower() == key), None)
    return None


def resolve_cost(
    cost_service: Any,
    *,
    project_id: str,
    cost_id: str | None,
) -> Any | None:
    if not cost_id:
        return None
    return next(
        (item for item in cost_service.list_cost_items_for_project(project_id) if item.id == cost_id),
        None,
    )


__all__ = [
    "build_project_lookup",
    "resolve_cost",
    "resolve_project",
    "resolve_task",
]
