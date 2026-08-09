"""Status coercion, reflection helpers and small utilities."""

from __future__ import annotations
from src.core.modules.project_management.domain.enums import ProjectStatus


def coerce_project_status(value: str | ProjectStatus | None) -> ProjectStatus:
    if isinstance(value, ProjectStatus):
        return value
    normalized = str(value or ProjectStatus.PLANNED.value).strip().upper()
    try:
        return ProjectStatus(normalized)
    except ValueError as exc:
        raise ValueError(f"Unsupported project status: {normalized}.") from exc

__all__ = ["coerce_project_status"]
