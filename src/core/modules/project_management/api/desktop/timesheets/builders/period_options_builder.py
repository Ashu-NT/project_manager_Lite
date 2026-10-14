from __future__ import annotations

from datetime import date

from src.core.modules.project_management.api.desktop.timesheets.formatters.period_formatter import (
    format_period_label,
)
from src.core.modules.project_management.api.desktop.timesheets.models.options import (
    TimesheetPeriodOptionDescriptor,
)
from src.core.modules.project_management.api.desktop.timesheets.utils.period_utils import (
    period_start,
)
from src.core.platform.application.time_management.time import (
    TimeEntryQueryHandler,
    TimesheetPeriodQueryHandler,
)


def build_period_options(
    assignment_id: str,
    *,
    resource_id: str,
    time_entry_queries: TimeEntryQueryHandler,
    period_queries: TimesheetPeriodQueryHandler,
) -> tuple[TimesheetPeriodOptionDescriptor, ...]:
    entries = time_entry_queries.list_time_entries_for_assignment(assignment_id)
    known_periods = {period_start(entry.entry_date) for entry in entries}
    known_periods.update(
        period.period_start
        for period in period_queries.list_timesheet_periods_for_resource(resource_id)
    )
    ordered_periods = sorted(known_periods, reverse=True)
    return tuple(
        TimesheetPeriodOptionDescriptor(
            value=current_period_start.isoformat(),
            label=format_period_label(current_period_start),
        )
        for current_period_start in ordered_periods
    )


def default_period_start(
    assignment_id: str,
    *,
    time_entry_queries: TimeEntryQueryHandler,
) -> date:
    entries = time_entry_queries.list_time_entries_for_assignment(assignment_id)
    target_date = max((entry.entry_date for entry in entries), default=date.today())  # noqa: DTZ011
    return period_start(target_date)


__all__ = ["build_period_options", "default_period_start"]
