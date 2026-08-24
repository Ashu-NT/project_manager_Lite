from __future__ import annotations

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
    project_names_from_ids,
)
from src.core.platform.application.time_management.time import TimesheetPeriodAggregate


def serialize_period_summary(
    *,
    aggregate: TimesheetPeriodAggregate,
    resource_name: str,
    project_names: tuple[str, ...],
) -> TimesheetPeriodSummaryDesktopDto:
    return TimesheetPeriodSummaryDesktopDto(
        period_id=aggregate.period_id,
        resource_id=aggregate.resource_id,
        resource_name=resource_name,
        period_start=aggregate.period_start,
        period_start_label=format_period_label(aggregate.period_start),
        period_end_label=aggregate.period_end.isoformat(),
        status=aggregate.status.value,
        status_label=aggregate.status.value.replace("_", " ").title(),
        submitted_by_username=aggregate.submitted_by_username or "-",
        submitted_at_label=format_datetime(aggregate.submitted_at),
        decided_by_username=aggregate.decided_by_username or "-",
        decided_at_label=format_datetime(aggregate.decided_at),
        decision_note=aggregate.decision_note,
        entry_count=aggregate.entry_count,
        total_hours=aggregate.total_hours,
        total_hours_label=format_hours(aggregate.total_hours),
        project_names=tuple(project_names),
        version=aggregate.version,
        project_count=len(aggregate.project_ids),
    )


def serialize_period_aggregate(
    aggregate: TimesheetPeriodAggregate,
    *,
    resource_service,
    project_service,
) -> TimesheetPeriodSummaryDesktopDto:
    resource = (
        resource_service.get_resource(aggregate.resource_id)
        if resource_service is not None
        else None
    )
    return serialize_period_summary(
        aggregate=aggregate,
        resource_name=getattr(resource, "name", aggregate.resource_id),
        project_names=project_names_from_ids(
            aggregate.project_ids,
            project_service=project_service,
        ),
    )


__all__ = ["serialize_period_aggregate", "serialize_period_summary"]
