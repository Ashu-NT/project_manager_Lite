from __future__ import annotations

from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_hours,
)
from src.core.modules.project_management.api.desktop.tasks.models.validation import (
    AssignmentPreviewDesktopDto,
)
from src.core.modules.project_management.api.desktop.tasks.services.capacity_status_labels import (
    capacity_status_label,
)


def build_assignment_preview(
    task_id: str,
    project_resource_id: str,
    *,
    task_service: object | None,
    project_resource_service: object | None,
    assignment_skill_validator: object | None,
    proposed_allocation_percent: float = 100.0,
    exclude_assignment_id: str | None = None,
    project_names: dict[str, str] | None = None,
) -> AssignmentPreviewDesktopDto:
    """Return combined availability + skill/cert check for an assignment
    candidate. Capacity comes from `TaskService.preview_assignment_capacity`
    -- the exact same authority save-time validation uses (docs §44) -- not
    a separate calculation."""
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
    capacity_known = False
    available_label = ""
    existing_label = ""
    proposed_label = ""
    resulting_label = ""
    peak_utilization_percent = 0.0
    capacity_status = "UNKNOWN"
    conflict_date_labels: tuple[str, ...] = ()
    preview_capacity = getattr(task_service, "preview_assignment_capacity", None)
    if callable(preview_capacity):
        fact = preview_capacity(
            task_id,
            resource_id,
            proposed_allocation_percent=proposed_allocation_percent,
            exclude_assignment_id=exclude_assignment_id,
        )
        if fact is not None:
            capacity_known = fact.effective_available_capacity_hours is not None
            if capacity_known:
                available_label = format_hours(fact.effective_available_capacity_hours)
                peak_utilization_percent = round(fact.peak_utilization_percent or 0.0, 1)
                overallocation_pct = max(0.0, peak_utilization_percent - 100.0)
            existing_label = format_hours(fact.existing_committed_capacity_hours)
            proposed_label = format_hours(fact.proposed_committed_capacity_hours)
            resulting_label = format_hours(fact.resulting_committed_capacity_hours)
            capacity_status = fact.capacity_status
            conflict_date_labels = tuple(d.isoformat() for d in fact.conflict_dates)

            if fact.is_over_capacity and task_service is not None:
                conflict_task_ids: set[str] = set()
                for day in fact.days:
                    if day.status == fact.capacity_status:
                        conflict_task_ids.update(day.contributing_task_ids)
                conflict_task_ids.discard(task_id)
                # Resolve names via the caller's pre-scoped, batched lookup
                # rather than per-conflict task_service.get_task calls plus
                # a `project_name` attribute Task doesn't have. A project the
                # current user isn't authorized to see simply won't resolve
                # a name here -- the capacity result still surfaces, the
                # other project's identity does not, without a second,
                # separate authorization check.
                names = project_names or {}
                for conflict_task_id in conflict_task_ids:
                    conflict_task = task_service.get_task(conflict_task_id)
                    if conflict_task is not None:
                        project_name = str(
                            names.get(getattr(conflict_task, "project_id", ""), "") or ""
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
        capacity_known=capacity_known,
        available_capacity_hours_label=available_label,
        existing_committed_hours_label=existing_label,
        proposed_committed_hours_label=proposed_label,
        resulting_committed_hours_label=resulting_label,
        peak_utilization_percent=peak_utilization_percent,
        capacity_status=capacity_status,
        capacity_status_label=capacity_status_label(capacity_status),
        conflict_date_labels=conflict_date_labels,
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
