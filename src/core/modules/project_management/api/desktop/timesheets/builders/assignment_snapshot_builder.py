from __future__ import annotations

from datetime import date

from src.core.modules.project_management.api.desktop.timesheets.builders.period_options_builder import (
    build_period_options,
    default_period_start,
)
from src.core.modules.project_management.api.desktop.timesheets.formatters.period_formatter import (
    format_period_label,
)
from src.core.modules.project_management.api.desktop.timesheets.formatters.time_formatter import (
    format_hours,
)
from src.core.modules.project_management.api.desktop.timesheets.models.options import (
    TimesheetAssignmentOptionDescriptor,
    TimesheetPeriodOptionDescriptor,
)
from src.core.modules.project_management.api.desktop.timesheets.models.snapshots import (
    TimesheetAssignmentSnapshotDesktopDto,
)
from src.core.modules.project_management.api.desktop.timesheets.serializers.entry_serializer import (
    serialize_entry,
)
from src.core.modules.project_management.api.desktop.timesheets.serializers.period_serializer import (
    serialize_period_summary,
)


def build_assignment_snapshot(
    assignment_id: str,
    *,
    period_start: date | None = None,
    project_service=None,
    task_service,
    resource_service=None,
    timesheet_service,
) -> TimesheetAssignmentSnapshotDesktopDto:
    normalized_assignment_id = str(assignment_id or "").strip()
    assignment = task_service.get_assignment(normalized_assignment_id)
    if assignment is None:
        raise RuntimeError("The selected task assignment could not be found.")
    task = task_service.get_task(assignment.task_id)
    if task is None:
        raise RuntimeError("The selected assignment task could not be found.")
    project = (
        project_service.get_project(task.project_id)
        if project_service is not None
        else None
    )
    resource = (
        resource_service.get_resource(assignment.resource_id)
        if resource_service is not None
        else None
    )
    assignment_option = TimesheetAssignmentOptionDescriptor(
        value=assignment.id,
        label=" | ".join(
            value
            for value in (
                getattr(project, "name", task.project_id),
                task.name,
                getattr(resource, "name", assignment.resource_id),
            )
            if value
        ),
        project_id=task.project_id,
        project_name=getattr(project, "name", task.project_id),
        task_id=task.id,
        task_name=task.name,
        resource_id=assignment.resource_id,
        resource_name=getattr(resource, "name", assignment.resource_id),
    )
    selected_period_start = period_start or default_period_start(
        assignment.id,
        timesheet_service=timesheet_service,
    )
    period_options = build_period_options(
        assignment.id,
        resource_id=assignment.resource_id,
        timesheet_service=timesheet_service,
    )
    if not period_options:
        period_options = (
            TimesheetPeriodOptionDescriptor(
                value=selected_period_start.isoformat(),
                label=format_period_label(selected_period_start),
            ),
        )
    if not any(
        option.value == selected_period_start.isoformat()
        for option in period_options
    ):
        selected_period_start = date.fromisoformat(period_options[0].value)
    task_entries = timesheet_service.list_time_entries_for_assignment_period(
        assignment.id,
        period_start=selected_period_start,
    )
    resource_entries = timesheet_service.list_time_entries_for_resource_period(
        assignment.resource_id,
        period_start=selected_period_start,
    )
    period = timesheet_service.get_timesheet_period(
        assignment.resource_id,
        period_start=selected_period_start,
    )
    resource_period_total_hours = sum(float(entry.hours or 0.0) for entry in resource_entries)
    resource_period_total_hours_label = format_hours(resource_period_total_hours)
    return TimesheetAssignmentSnapshotDesktopDto(
        assignment=assignment_option,
        period_options=period_options,
        selected_period_start=selected_period_start.isoformat(),
        period_summary=serialize_period_summary(
            period=period,
            resource_id=assignment.resource_id,
            resource_name=assignment_option.resource_name,
            period_start=selected_period_start,
            entries=resource_entries,
            project_names=(assignment_option.project_name,),
        ),
        entries=tuple(
            serialize_entry(entry, assignment.id)
            for entry in task_entries
        ),
        resource_period_total_hours_label=resource_period_total_hours_label,
        scope_summary=(
            f"Task period entries: {len(task_entries)} | Resource month total: "
            f"{resource_period_total_hours_label}"
        ),
    )


__all__ = ["build_assignment_snapshot"]
