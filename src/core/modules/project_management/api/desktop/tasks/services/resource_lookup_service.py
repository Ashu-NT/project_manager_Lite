from __future__ import annotations


def resource_by_id(
    *,
    resource_service: object | None,
    resource_ids: tuple[str, ...] | None = None,
) -> dict[str, object]:
    if resource_service is None:
        return {}
    list_for_task_workspace = getattr(resource_service, "list_for_task_workspace", None)
    if not callable(list_for_task_workspace):
        return {}
    normalized_ids = tuple(
        sorted(
            {
                str(resource_id or "").strip()
                for resource_id in (resource_ids or ())
                if str(resource_id or "").strip()
            }
        )
    )
    resources = list(list_for_task_workspace(resource_ids=normalized_ids))
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
