"""Resource lookup, resolution and assignable resource option assembly."""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.projects.models.resources import (
    ProjectAssignableResourceOptionDescriptor,
)
from src.core.modules.project_management.api.desktop.projects.serializers.resource_serializer import (
    assignable_resource_label,
)
from src.core.modules.project_management.application.resources.dto.responses.catalog import (
    ResourceResponse,
)
from src.core.modules.project_management.application.resources.queries.resource_queries import (
    ResourceQueryHandler,
)


def resource_lookup(
    project_id: str,
    resource_ids: tuple[str, ...],
    *,
    resource_query: ResourceQueryHandler | None = None,
) -> dict[str, ResourceResponse]:
    resources = list_resources_for_context(
        project_id, resource_ids=resource_ids,
        resource_query=resource_query,
    )
    return {
        str(r.id): r
        for r in resources
        if r is not None and getattr(r, "id", None)
    }


def list_resources_for_context(
    project_id: str,
    *,
    resource_ids: tuple[str, ...] | None = None,
    resource_query: ResourceQueryHandler | None = None,
) -> tuple[ResourceResponse, ...]:
    if resource_query is None:
        return ()
    resources = list(
        resource_query.list_for_project_workspace(
            project_id,
            resource_ids=tuple(resource_ids or ()),
        )
    )
    return tuple(r for r in resources if r is not None)


def build_assignable_options(
    project_id: str,
    assigned_resource_ids: set[str],
    *,
    resource_query: ResourceQueryHandler | None = None,
) -> tuple[ProjectAssignableResourceOptionDescriptor, ...]:
    resources = list_resources_for_context(
        project_id, resource_query=resource_query
    )
    options = [
        ProjectAssignableResourceOptionDescriptor(
            value=str(r.id),
            label=assignable_resource_label(r),
        )
        for r in resources
        if getattr(r, "id", None)
        and bool(getattr(r, "is_active", True))
        and str(r.id) not in assigned_resource_ids
    ]
    return tuple(sorted(options, key=lambda o: o.label.casefold()))


__all__ = ["build_assignable_options", "list_resources_for_context", "resource_lookup"]
