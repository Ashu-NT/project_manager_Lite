from __future__ import annotations

from src.core.modules.project_management.api.desktop.tasks.models.options import (
    TaskProjectResourceOptionDescriptor,
)
from src.core.modules.project_management.api.desktop.tasks.services.access_resolution_service import (
    can_fallback_task_project,
)
from src.core.platform.common.exceptions import BusinessRuleError


def build_project_resource_options(
    project_id: str,
    *,
    project_resource_service: object | None,
    resource_service: object | None,
    task_service: object | None,
) -> tuple[TaskProjectResourceOptionDescriptor, ...]:
    if not project_id or project_resource_service is None or resource_service is None:
        return ()
    list_by_project = getattr(project_resource_service, "list_by_project", None)
    list_resources = getattr(resource_service, "list_resources", None)
    if not callable(list_by_project) or not callable(list_resources):
        return ()
    try:
        project_resources = list_by_project(project_id)
    except BusinessRuleError as exc:
        if not can_fallback_task_project(
            project_id,
            exc,
            task_service=task_service,
        ):
            raise
        project_resource_repo = getattr(
            project_resource_service,
            "_project_resource_repo",
            None,
        )
        if project_resource_repo is None:
            return ()
        project_resources = list(project_resource_repo.list_by_project(project_id))
    try:
        resources = list_resources()
    except BusinessRuleError as exc:
        if not can_fallback_task_project(
            project_id,
            exc,
            task_service=task_service,
        ):
            raise
        resource_repo = getattr(resource_service, "_resource_repo", None)
        if resource_repo is None:
            return ()
        resource_ids = {
            str(getattr(project_resource, "resource_id", "") or "")
            for project_resource in project_resources
            if str(getattr(project_resource, "resource_id", "") or "").strip()
        }
        resources = [
            resource_repo.get(resource_id)
            for resource_id in sorted(resource_ids)
        ]
    resources_by_id = {
        resource.id: resource
        for resource in resources
        if resource is not None
    }
    options: list[TaskProjectResourceOptionDescriptor] = []
    for project_resource in project_resources:
        resource = resources_by_id.get(project_resource.resource_id)
        if resource is None:
            continue
        if not getattr(project_resource, "is_active", True) or not getattr(
            resource,
            "is_active",
            True,
        ):
            continue
        rate = (
            getattr(project_resource, "hourly_rate", None)
            if getattr(project_resource, "hourly_rate", None) is not None
            else getattr(resource, "hourly_rate", None)
        )
        currency = (
            getattr(project_resource, "currency_code", None)
            or getattr(resource, "currency_code", None)
            or ""
        ).upper()
        label = str(getattr(resource, "name", "") or project_resource.resource_id)
        if rate is not None:
            rate_label = f"{float(rate):.2f}"
            if currency:
                label += f" ({rate_label} {currency}/hr)"
            else:
                label += f" ({rate_label}/hr)"
        options.append(
            TaskProjectResourceOptionDescriptor(
                value=project_resource.id,
                label=label,
            )
        )
    return tuple(sorted(options, key=lambda option: option.label.casefold()))


__all__ = ["build_project_resource_options"]
