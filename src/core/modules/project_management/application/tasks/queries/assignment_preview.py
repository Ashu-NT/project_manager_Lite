from __future__ import annotations

from src.core.modules.project_management.application.tasks.dto.responses.assignment_validation import (
    AssignmentPreviewResponseDto,
)
from src.core.modules.project_management.application.resources.catalog.assignment_validation import (
    AssignmentSkillValidator,
)
from src.core.modules.project_management.application.tasks.commands.assignment import (
    TaskAssignmentCommandHandler,
)
from src.core.modules.project_management.application.tasks.queries.task_detail_page import (
    TaskDetailPageQueryHandler,
)


def query_assignment_preview(
    task_id: str,
    project_resource_id: str,
    *,
    task_query: TaskDetailPageQueryHandler | None,
    assignment_commands: TaskAssignmentCommandHandler | None,
    project_resource_query: object | None,
    assignment_skill_validator: AssignmentSkillValidator | None,
    proposed_allocation_percent: float = 100.0,
    exclude_assignment_id: str | None = None,
) -> AssignmentPreviewResponseDto:
    """Return combined availability + skill/cert check for an assignment
    candidate. Capacity comes from `TaskAssignmentCommandHandler.preview_assignment_capacity`
    -- the exact same authority save-time validation uses -- not a
    separate calculation."""
    empty_preview = _empty_assignment_preview(task_id)
    if not task_id or not project_resource_id:
        return empty_preview

    resource_id = ""
    get_project_resource = getattr(project_resource_query, "get", None)
    if callable(get_project_resource):
        project_resource = get_project_resource(project_resource_id)
        resource_id = (
            str(getattr(project_resource, "resource_id", "") or "")
            if project_resource
            else ""
        )
    if not resource_id:
        return empty_preview

    overallocation_pct = 0.0
    conflict_projects: list[str] = []
    fact = None
    preview_capacity = getattr(assignment_commands, "preview_assignment_capacity", None)
    if callable(preview_capacity):
        fact = preview_capacity(
            task_id,
            resource_id,
            proposed_allocation_percent=proposed_allocation_percent,
            exclude_assignment_id=exclude_assignment_id,
        )
        if fact is not None:
            if fact.effective_available_capacity_hours is not None:
                peak = round(fact.peak_utilization_percent or 0.0, 1)
                overallocation_pct = max(0.0, peak - 100.0)

            if fact.is_over_capacity and task_query is not None:
                conflict_task_ids: set[str] = set()
                for day in fact.days:
                    if day.status == fact.capacity_status:
                        conflict_task_ids.update(day.contributing_task_ids)
                conflict_task_ids.discard(task_id)
                for conflict_task in task_query.list_tasks_by_ids(sorted(conflict_task_ids)):
                    if conflict_task.project_id not in conflict_projects:
                        conflict_projects.append(conflict_task.project_id)

    skills_matched = True
    certs_valid = True
    has_warnings = False
    warning_messages: list[str] = []
    is_blocked = False
    block_messages: list[str] = []
    if assignment_skill_validator is not None and task_query is not None:
        task = task_query.get_task(task_id)
        if task is not None:
            result = assignment_skill_validator.validate(task, resource_id)
            skills_matched = not any(
                violation.violation_type
                in ("missing_skill", "insufficient_proficiency")
                for violation in result.violations
            )
            certs_valid = not any(
                violation.violation_type
                in ("missing_certification", "expired_certification")
                for violation in result.violations
            )
            is_blocked = result.is_blocked
            block_messages = [violation.message for violation in result.violations]
            has_warnings = bool(result.warnings)
            warning_messages = [warning.message for warning in result.warnings]

    return AssignmentPreviewResponseDto(
        task_id=task_id,
        resource_id=resource_id,
        overallocation_pct=round(overallocation_pct, 1),
        conflict_project_ids=tuple(conflict_projects),
        skills_matched=skills_matched,
        certs_valid=certs_valid,
        has_warnings=has_warnings,
        warning_messages=tuple(warning_messages),
        is_blocked=is_blocked,
        block_messages=tuple(block_messages),
        capacity=fact,
    )


def _empty_assignment_preview(task_id: str) -> AssignmentPreviewResponseDto:
    return AssignmentPreviewResponseDto(
        task_id=task_id,
        resource_id="",
        overallocation_pct=0.0,
        conflict_project_ids=(),
        skills_matched=True,
        certs_valid=True,
        has_warnings=False,
        warning_messages=(),
        is_blocked=False,
        block_messages=(),
    )


__all__ = ["query_assignment_preview"]
