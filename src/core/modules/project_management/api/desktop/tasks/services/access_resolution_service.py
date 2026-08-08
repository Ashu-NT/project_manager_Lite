from __future__ import annotations


def project_rows_for_task_scope(
    *,
    project_service: object | None,
) -> tuple[object, ...]:
    if project_service is None:
        return ()
    list_for_task_workspace = getattr(project_service, "list_for_task_workspace", None)
    if not callable(list_for_task_workspace):
        return ()
    projects = list(list_for_task_workspace())
    return tuple(
        sorted(
            (project for project in projects if project is not None),
            key=lambda project: (str(getattr(project, "name", "") or "")).casefold(),
        )
    )


__all__ = ["project_rows_for_task_scope"]
