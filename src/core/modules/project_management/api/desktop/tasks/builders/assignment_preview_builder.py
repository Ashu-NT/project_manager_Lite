from __future__ import annotations

from src.core.modules.project_management.api.desktop.tasks.models.validation import (
    AssignmentPreviewDesktopDto,
)


def build_assignment_preview(
    task_id: str,
    project_resource_id: str,
    *,
    task_service: object | None,
    project_resource_service: object | None,
    assignment_skill_validator: object | None,
    resource_availability_service: object | None,
) -> AssignmentPreviewDesktopDto:
    """Return combined availability + skill/cert check for an assignment candidate."""
    empty_preview = _empty_assignment_preview(task_id)
    if not task_id or not project_resource_id:
        return empty_preview

    resource_id = ""
    get_project_resource = getattr(project_resource_service, "get", None)
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
    if resource_availability_service is not None and task_service is not None:
        task = task_service.get_task(task_id)
        if task is not None:
            p_start = getattr(task, "start_date", None)
            p_finish = getattr(task, "end_date", None)
            if p_start and p_finish:
                _, window = resource_availability_service.is_resource_available(
                    resource_id,
                    p_start,
                    p_finish,
                )
                if window is not None and window.peak_load_percent > window.capacity_percent:
                    overallocation_pct = max(
                        0.0,
                        window.peak_load_percent - window.capacity_percent,
                    )
                    conflict_task_ids: set[str] = set()
                    for day in window.daily_loads:
                        if day.overloaded:
                            conflict_task_ids.update(day.contributing_tasks)
                    conflict_task_ids.discard(task_id)
                    for conflict_task_id in conflict_task_ids:
                        conflict_task = task_service.get_task(conflict_task_id)
                        if conflict_task is not None:
                            project_name = str(
                                getattr(conflict_task, "project_name", "") or ""
                            )
                            if project_name and project_name not in conflict_projects:
                                conflict_projects.append(project_name)

    skills_matched = True
    certs_valid = True
    has_warnings = False
    warning_messages: list[str] = []
    is_blocked = False
    block_messages: list[str] = []
    if assignment_skill_validator is not None and task_service is not None:
        task = task_service.get_task(task_id)
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

    return AssignmentPreviewDesktopDto(
        task_id=task_id,
        resource_id=resource_id,
        overallocation_pct=round(overallocation_pct, 1),
        conflict_projects=tuple(conflict_projects),
        skills_matched=skills_matched,
        certs_valid=certs_valid,
        has_warnings=has_warnings,
        warning_messages=tuple(warning_messages),
        is_blocked=is_blocked,
        block_messages=tuple(block_messages),
    )


def _empty_assignment_preview(task_id: str) -> AssignmentPreviewDesktopDto:
    return AssignmentPreviewDesktopDto(
        task_id=task_id,
        resource_id="",
        overallocation_pct=0.0,
        conflict_projects=(),
        skills_matched=True,
        certs_valid=True,
        has_warnings=False,
        warning_messages=(),
        is_blocked=False,
        block_messages=(),
    )


__all__ = ["build_assignment_preview"]
