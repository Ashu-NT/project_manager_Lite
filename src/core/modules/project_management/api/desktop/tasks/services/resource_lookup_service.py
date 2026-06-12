from __future__ import annotations

from src.core.modules.project_management.api.desktop.tasks.services.access_resolution_service import (
    task_user_session,
)
from src.core.platform.common.exceptions import BusinessRuleError


def resource_by_id(
    *,
    resource_service: object | None,
    task_service: object | None = None,
    resource_ids: tuple[str, ...] | None = None,
) -> dict[str, object]:
    if resource_service is None:
        return {}
    list_resources = getattr(resource_service, "list_resources", None)
    if not callable(list_resources):
        return {}
    normalized_ids = tuple(
        {
            str(resource_id or "").strip()
            for resource_id in (resource_ids or ())
            if str(resource_id or "").strip()
        }
    )
    resources: list[object]
    try:
        resources = list(list_resources())
    except BusinessRuleError as exc:
        if "resource.read" not in str(exc):
            raise
        resource_repo = getattr(resource_service, "_resource_repo", None)
        user_session = task_user_session(task_service)
        if resource_repo is None or user_session is None:
            return {}
        if not (
            user_session.has_permission("task.read")
            or user_session.has_permission("task.manage")
        ):
            return {}
        tenant_context = getattr(resource_service, "_tenant_context_service", None) or getattr(
            task_service, "_tenant_context_service", None
        )
        organization_id = (
            tenant_context.require_active_organization_id(operation_label="list task resources")
            if tenant_context is not None
            else None
        )
        if not organization_id:
            return {}
        resources = list(resource_repo.list_for_organization(organization_id))
        if normalized_ids:
            resources = [
                resource
                for resource in resources
                if str(getattr(resource, "id", "") or "").strip() in normalized_ids
            ]
    return {
        resource.id: resource
        for resource in resources
        if resource is not None
    }


def resource_name_for_assignment(
    assignment,
    *,
    resources_by_id: dict[str, object],
) -> str:
    resource = resources_by_id.get(assignment.resource_id)
    return str(
        getattr(resource, "name", "") or getattr(assignment, "resource_id", "")
    )


__all__ = ["resource_by_id", "resource_name_for_assignment"]
