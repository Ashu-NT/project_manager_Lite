"""Status coercion, reflection helpers and small utilities."""

from __future__ import annotations
from datetime import date

from src.core.modules.project_management.domain.enums import ProjectStatus


def coerce_project_status(value: str | ProjectStatus | None) -> ProjectStatus:
    if isinstance(value, ProjectStatus):
        return value
    normalized = str(value or ProjectStatus.PLANNED.value).strip().upper()
    try:
        return ProjectStatus(normalized)
    except ValueError as exc:
        raise ValueError(f"Unsupported project status: {normalized}.") from exc


def optional_date(value: str | None) -> date | None:
    text = str(value or "").strip()
    return date.fromisoformat(text) if text else None


__all__ = ["coerce_project_status", "optional_date"]
