from __future__ import annotations

from src.core.modules.project_management.api.desktop.tasks.models.validation import (
    AssignmentValidationDesktopDto,
)


def build_assignment_validation(
    task_id: str,
    project_resource_id: str,
    *,
    task_service: object | None,
    project_resource_service: object | None,
    assignment_skill_validator: object | None,
) -> AssignmentValidationDesktopDto:
    if assignment_skill_validator is None or project_resource_service is None:
        return _valid_assignment(task_id)
    if task_service is None:
        raise RuntimeError("Project management tasks desktop API is not connected.")
    task = task_service.get_task(task_id)
    if task is None:
        return _valid_assignment(task_id)
    get_project_resource = getattr(project_resource_service, "get", None)
    if not callable(get_project_resource):
        resource_id = ""
    else:
        project_resource = get_project_resource(project_resource_id)
        resource_id = (
            str(getattr(project_resource, "resource_id", "") or "")
            if project_resource
            else ""
        )
    if not resource_id:
        return _valid_assignment(task_id)
    result = assignment_skill_validator.validate(task, resource_id)
    return AssignmentValidationDesktopDto(
        task_id=task_id,
        resource_id=resource_id,
        is_valid=result.is_valid,
        can_assign=result.can_assign,
        requires_approval=result.requires_approval,
        is_blocked=result.is_blocked,
        has_warnings=bool(result.warnings),
        violation_messages=tuple(v.message for v in result.violations),
        warning_messages=tuple(w.message for w in result.warnings),
        summary=result.summary(),
    )


def _valid_assignment(task_id: str) -> AssignmentValidationDesktopDto:
    return AssignmentValidationDesktopDto(
        task_id=task_id,
        resource_id="",
        is_valid=True,
        can_assign=True,
        requires_approval=False,
        is_blocked=False,
        has_warnings=False,
        violation_messages=(),
        warning_messages=(),
        summary="valid",
    )


__all__ = ["build_assignment_validation"]
