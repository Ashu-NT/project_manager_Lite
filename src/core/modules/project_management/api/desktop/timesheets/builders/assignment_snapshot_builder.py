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
    task_service,
    timesheet_service,
) -> TimesheetAssignmentSnapshotDesktopDto:
    normalized_assignment_id = str(assignment_id or "").strip()
    context = task_service.get_timesheet_assignment_context(normalized_assignment_id)
    if context is None:
        raise RuntimeError("The selected task assignment could not be found.")
    assignment_option = TimesheetAssignmentOptionDescriptor(
        value=context.assignment_id,
        label=f"{context.project_name} | {context.task_name} | {context.resource_name}",
        project_id=context.project_id,
        project_name=context.project_name,
        task_id=context.task_id,
        task_name=context.task_name,
        resource_id=context.resource_id,
        resource_name=context.resource_name,
    )
    selected_period_start = period_start or default_period_start(
        context.assignment_id,
        timesheet_service=timesheet_service,
    )
    period_options = build_period_options(
        context.assignment_id,
        resource_id=context.resource_id,
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
        context.assignment_id,
        period_start=selected_period_start,
    )
    resource_entries = timesheet_service.list_time_entries_for_resource_period(
        context.resource_id,
        period_start=selected_period_start,
    )
    period = timesheet_service.get_timesheet_period(
        context.resource_id,
        period_start=selected_period_start,
    )
    period_aggregate = timesheet_service.summarize_timesheet_period(
        context.resource_id,
        period_start=selected_period_start,
        period=period,
        entries=resource_entries,
    )
    resource_period_total_hours_label = format_hours(period_aggregate.total_hours)
    task_period_hours = sum((float(entry.hours or 0.0) for entry in task_entries), 0.0)
    task_period_hours_label = format_hours(task_period_hours)

    assignment = task_service.get_assignment(context.assignment_id)
    planned_hours = float(getattr(assignment, "allocated_planned_hours", 0) or 0) if assignment else 0.0
    logged_hours = float(getattr(assignment, "hours_logged", 0) or 0) if assignment else 0.0
    remaining_hours = planned_hours - logged_hours

    return TimesheetAssignmentSnapshotDesktopDto(
        assignment=assignment_option,
        period_options=period_options,
        selected_period_start=selected_period_start.isoformat(),
        period_summary=serialize_period_summary(
            aggregate=period_aggregate,
            resource_name=assignment_option.resource_name,
            project_names=(assignment_option.project_name,),
        ),
        entries=tuple(
            serialize_entry(entry, context.assignment_id)
            for entry in task_entries
        ),
        resource_period_total_hours_label=resource_period_total_hours_label,
        scope_summary=(
            f"Task period entries: {len(task_entries)} | Resource month total: "
            f"{resource_period_total_hours_label}"
        ),
        task_period_hours_label=task_period_hours_label,
        planned_hours_label=format_hours(planned_hours),
        logged_hours_label=format_hours(logged_hours),
        remaining_hours_label=format_hours(remaining_hours),
    )


__all__ = ["build_assignment_snapshot"]
