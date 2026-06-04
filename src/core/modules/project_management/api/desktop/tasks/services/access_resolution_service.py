from __future__ import annotations

from src.core.platform.common.exceptions import BusinessRuleError


def project_rows_for_task_scope(
    *,
    project_service: object | None,
    task_service: object | None,
) -> tuple[object, ...]:
    if project_service is None:
        return ()
    try:
        projects = list(project_service.list_projects())
    except BusinessRuleError as exc:
        if "project.read" not in str(exc):
            raise
        project_repo = getattr(project_service, "_project_repo", None)
        user_session = task_user_session(task_service)
        if project_repo is None or user_session is None:
            return ()
        project_ids: set[str] = set()
        for permission_code in ("task.read", "task.manage", "project.read"):
            project_ids.update(user_session.project_ids_for(permission_code))
        if project_ids:
            projects = [
                project_repo.get(project_id)
                for project_id in sorted(project_ids)
            ]
        elif user_session.has_permission("task.read") or user_session.has_permission(
            "task.manage"
        ):
            projects = list(project_repo.list_all())
        else:
            projects = []
    return tuple(
        sorted(
            (project for project in projects if project is not None),
            key=lambda project: (str(getattr(project, "name", "") or "")).casefold(),
        )
    )


def task_user_session(task_service: object | None):
    if task_service is None:
        return None
    return getattr(task_service, "_user_session", None)


def can_fallback_task_project(
    project_id: str,
    exc: BusinessRuleError,
    *,
    task_service: object | None,
) -> bool:
    message = str(exc)
    if "project.read" not in message and "resource.read" not in message:
        return False
    normalized_project_id = str(project_id or "").strip()
    if not normalized_project_id:
        return False
    user_session = task_user_session(task_service)
    if user_session is None:
        return False
    if user_session.has_project_permission(normalized_project_id, "task.read"):
        return True
    if user_session.has_project_permission(normalized_project_id, "task.manage"):
        return True
    if (
        not user_session.is_project_restricted()
        and (
            user_session.has_permission("task.read")
            or user_session.has_permission("task.manage")
        )
    ):
        return True
    return False


__all__ = [
    "can_fallback_task_project",
    "project_rows_for_task_scope",
    "task_user_session",
]
