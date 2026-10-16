from src.core.modules.project_management.application.resources.catalog.assignment_validation import (
    AssignmentValidationResult,
)
from src.core.modules.project_management.application.tasks.dto.responses.assignment_validation import (
    AssignmentValidationResponseDto,
)


def map_assignment_validation(
    result: AssignmentValidationResult,
) -> AssignmentValidationResponseDto:
    return AssignmentValidationResponseDto(
        task_id=result.task_id,
        resource_id=result.resource_id,
        is_valid=result.is_valid,
        can_assign=result.can_assign,
        requires_approval=result.requires_approval,
        is_blocked=result.is_blocked,
        has_warnings=bool(result.warnings),
        violation_messages=tuple(item.message for item in result.violations),
        warning_messages=tuple(item.message for item in result.warnings),
        summary=result.summary(),
    )
