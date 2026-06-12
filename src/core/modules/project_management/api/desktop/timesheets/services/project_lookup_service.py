from __future__ import annotations


def project_name_for_id(
    project_id: str | None,
    *,
    project_service,
) -> str:
    normalized_id = str(project_id or "").strip()
    if not normalized_id or project_service is None:
        return normalized_id
    project = project_service.get_project(normalized_id)
    return getattr(project, "name", normalized_id)


def project_names_from_ids(
    project_ids,
    *,
    project_service,
) -> tuple[str, ...]:
    names = [
        project_name_for_id(project_id, project_service=project_service)
        for project_id in project_ids or ()
    ]
    return tuple(name for name in names if name)


def project_names_for_entries(
    entries,
    *,
    project_service,
) -> tuple[str, ...]:
    project_names = {
        project_name_for_id(
            getattr(entry, "scope_id", None),
            project_service=project_service,
        )
        for entry in entries
        if getattr(entry, "scope_type", None) == "project"
    }
    return tuple(sorted(name for name in project_names if name))


__all__ = [
    "project_name_for_id",
    "project_names_for_entries",
    "project_names_from_ids",
]
