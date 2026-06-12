"""Project resource and assignable resource serializers."""

from src.core.modules.project_management.api.desktop.projects.models.resources import ProjectResourceDesktopDto
from src.core.modules.project_management.api.desktop.projects.formatters.resource_formatters import (
    format_hourly_rate,
    format_hours,
)


def serialize_project_resource(project_resource, *, resource_by_id) -> ProjectResourceDesktopDto:
    resolved_currency = (
        str(
            getattr(project_resource, "currency_code", None)
            or getattr(resource_by_id, "currency_code", None)
            or ""
        ).strip().upper()
        or None
    )
    resolved_rate = (
        getattr(project_resource, "hourly_rate", None)
        if getattr(project_resource, "hourly_rate", None) is not None
        else getattr(resource_by_id, "hourly_rate", None)
    )
    worker_type_raw = str(getattr(resource_by_id, "worker_type", "") or "")
    worker_type_label = worker_type_raw.replace("_", " ").title() if worker_type_raw else "Unknown"
    is_active = bool(getattr(project_resource, "is_active", True))
    planned_hours = float(getattr(project_resource, "planned_hours", 0.0) or 0.0)
    return ProjectResourceDesktopDto(
        id=str(getattr(project_resource, "id", "") or ""),
        project_id=str(getattr(project_resource, "project_id", "") or ""),
        resource_id=str(getattr(project_resource, "resource_id", "") or ""),
        resource_name=str(
            getattr(resource_by_id, "name", "")
            or getattr(project_resource, "resource_id", "")
            or "Unknown resource"
        ),
        role=str(getattr(resource_by_id, "role", "") or ""),
        worker_type_label=worker_type_label,
        hourly_rate=resolved_rate,
        hourly_rate_label=format_hourly_rate(resolved_rate, resolved_currency),
        currency_code=resolved_currency,
        planned_hours=planned_hours,
        planned_hours_label=format_hours(planned_hours),
        is_active=is_active,
        status_label="Active" if is_active else "Inactive",
    )


def assignable_resource_label(resource) -> str:
    name = str(getattr(resource, "name", "") or "Unnamed resource")
    role = str(getattr(resource, "role", "") or "")
    hourly_rate = getattr(resource, "hourly_rate", None)
    currency_code = str(getattr(resource, "currency_code", "") or "").strip().upper() or None
    details: list[str] = []
    if role:
        details.append(role)
    if hourly_rate is not None:
        details.append(format_hourly_rate(hourly_rate, currency_code))
    return f"{name} | {' | '.join(details)}" if details else name


__all__ = ["assignable_resource_label", "serialize_project_resource"]
