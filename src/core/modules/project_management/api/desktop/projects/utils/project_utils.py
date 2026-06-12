"""Status coercion, reflection helpers and small utilities."""

from __future__ import annotations
import inspect

from src.core.modules.project_management.domain.enums import ProjectStatus


def coerce_project_status(value: str | ProjectStatus | None) -> ProjectStatus:
    if isinstance(value, ProjectStatus):
        return value
    normalized = str(value or ProjectStatus.PLANNED.value).strip().upper()
    try:
        return ProjectStatus(normalized)
    except ValueError as exc:
        raise ValueError(f"Unsupported project status: {normalized}.") from exc


def call_with_supported_kwargs(method, *args, **kwargs):
    """Call method, filtering kwargs to only those supported by the signature."""
    parameters = inspect.signature(method).parameters
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in parameters.values()):
        return method(*args, **kwargs)
    supported = {name: value for name, value in kwargs.items() if name in parameters}
    return method(*args, **supported)


__all__ = ["call_with_supported_kwargs", "coerce_project_status"]
