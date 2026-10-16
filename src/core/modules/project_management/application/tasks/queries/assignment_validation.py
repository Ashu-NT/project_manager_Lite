from __future__ import annotations

from src.core.modules.project_management.application.tasks.dto.responses.assignment_validation import (
    AssignmentValidationResponseDto,
)
from src.core.modules.project_management.application.tasks.mappers.assignment_validation import map_assignment_validation
from src.core.modules.project_management.application.resources.catalog.assignment_validation import (
    AssignmentSkillValidator,
)
from src.core.modules.project_management.application.tasks.queries.task_detail_page import (
    TaskDetailPageQueryHandler,
)
from src.core.platform.common.exceptions import ConfigurationError


def query_assignment_validation(
    task_id: str,
    project_resource_id: str,
    *,
    task_query: TaskDetailPageQueryHandler | None,
    project_resource_query: object | None,
    assignment_skill_validator: AssignmentSkillValidator | None,
) -> AssignmentValidationResponseDto:
    if assignment_skill_validator is None or project_resource_query is None:
        return _valid_assignment(task_id)
    if task_query is None:
        raise ConfigurationError("Project management tasks desktop API is not connected.")
    task = task_query.get_task(task_id)
    if task is None:
        return _valid_assignment(task_id)
    get_project_resource = getattr(project_resource_query, "get", None)
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
    return map_assignment_validation(result)


def _valid_assignment(task_id: str) -> AssignmentValidationResponseDto:
    return AssignmentValidationResponseDto(
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


__all__ = ["query_assignment_validation"]
