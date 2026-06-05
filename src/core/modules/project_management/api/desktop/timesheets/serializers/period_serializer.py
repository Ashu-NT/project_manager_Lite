from __future__ import annotations

from datetime import date

from src.core.modules.project_management.api.desktop.timesheets.formatters.datetime_formatter import (
    format_datetime,
)
from src.core.modules.project_management.api.desktop.timesheets.formatters.period_formatter import (
    format_period_label,
)
from src.core.modules.project_management.api.desktop.timesheets.formatters.time_formatter import (
    format_hours,
)
from src.core.modules.project_management.api.desktop.timesheets.models.periods import (
    TimesheetPeriodSummaryDesktopDto,
)
from src.core.modules.project_management.api.desktop.timesheets.services.project_lookup_service import (
    project_names_for_entries,
)
from src.core.modules.project_management.api.desktop.timesheets.utils.period_utils import (
    period_end,
)
from src.core.platform.time.domain import TimesheetPeriodStatus


def serialize_period_summary(
    *,
    period,
    resource_id: str,
    resource_name: str,
    period_start: date,
    entries,
    project_names: tuple[str, ...],
) -> TimesheetPeriodSummaryDesktopDto:
    total_hours = float(sum(float(entry.hours or 0.0) for entry in entries))
    if period is None:
        status = TimesheetPeriodStatus.OPEN
        period_id = ""
        submitted_by_username = "-"
        submitted_at_label = "-"
        decided_by_username = "-"
        decided_at_label = "-"
        decision_note = ""
        period_end_label = period_end(period_start).isoformat()
    else:
        status = period.status
        period_id = period.id
        submitted_by_username = period.submitted_by_username or "-"
        submitted_at_label = format_datetime(period.submitted_at)
        decided_by_username = period.decided_by_username or "-"
        decided_at_label = format_datetime(period.decided_at)
        decision_note = period.decision_note or ""
        period_end_label = period.period_end.isoformat()
    return TimesheetPeriodSummaryDesktopDto(
        period_id=period_id,
        resource_id=resource_id,
        resource_name=resource_name,
        period_start=period_start,
        period_start_label=format_period_label(period_start),
        period_end_label=period_end_label,
        status=status.value,
        status_label=status.value.replace("_", " ").title(),
        submitted_by_username=submitted_by_username,
        submitted_at_label=submitted_at_label,
        decided_by_username=decided_by_username,
        decided_at_label=decided_at_label,
        decision_note=decision_note,
        entry_count=len(entries),
        total_hours=total_hours,
        total_hours_label=format_hours(total_hours),
        project_names=tuple(project_names),
    )


def serialize_period_from_service(
    period,
    *,
    timesheet_service,
    resource_service,
    project_service,
) -> TimesheetPeriodSummaryDesktopDto:
    resource_entries = timesheet_service.list_time_entries_for_resource_period(
        period.resource_id,
        period_start=period.period_start,
    )
    resource = (
        resource_service.get_resource(period.resource_id)
        if resource_service is not None
        else None
    )
    return serialize_period_summary(
        period=period,
        resource_id=period.resource_id,
        resource_name=getattr(resource, "name", period.resource_id),
        period_start=period.period_start,
        entries=resource_entries,
        project_names=tuple(
            project_names_for_entries(resource_entries, project_service=project_service)
        ),
    )


__all__ = ["serialize_period_from_service", "serialize_period_summary"]
