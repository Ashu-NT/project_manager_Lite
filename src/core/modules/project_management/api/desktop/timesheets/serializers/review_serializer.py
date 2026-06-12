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
from src.core.modules.project_management.api.desktop.timesheets.models.review import (
    TimesheetReviewDetailDesktopDto,
    TimesheetReviewEntryDesktopDto,
)
from src.core.modules.project_management.api.desktop.timesheets.services.project_lookup_service import (
    project_name_for_id,
    project_names_from_ids,
)
from src.core.platform.time.application import TimesheetReviewDetail


def serialize_review_summary(
    row,
    *,
    project_service,
) -> TimesheetPeriodSummaryDesktopDto:
    return TimesheetPeriodSummaryDesktopDto(
        period_id=row.period_id,
        resource_id=row.resource_id,
        resource_name=row.resource_name,
        period_start=row.period_start,
        period_start_label=format_period_label(row.period_start),
        period_end_label=row.period_end.isoformat(),
        status=row.status.value,
        status_label=row.status.value.replace("_", " ").title(),
        submitted_by_username=row.submitted_by_username or "-",
        submitted_at_label=format_datetime(row.submitted_at),
        decided_by_username=row.decided_by_username or "-",
        decided_at_label=format_datetime(row.decided_at),
        decision_note=row.decision_note or "",
        entry_count=int(row.entry_count or 0),
        total_hours=float(row.total_hours or 0.0),
        total_hours_label=format_hours(row.total_hours),
        project_names=tuple(
            project_names_from_ids(row.project_ids, project_service=project_service)
        ),
    )


def serialize_review_detail(
    detail: TimesheetReviewDetail,
    *,
    project_service,
) -> TimesheetReviewDetailDesktopDto:
    return TimesheetReviewDetailDesktopDto(
        summary=serialize_review_summary(
            detail.summary,
            project_service=project_service,
        ),
        entries=tuple(
            TimesheetReviewEntryDesktopDto(
                entry_id=entry.entry_id,
                entry_date_label=entry.entry_date.isoformat(),
                project_name=project_name_for_id(
                    entry.project_id,
                    project_service=project_service,
                ),
                task_name=entry.task_name or "-",
                hours_label=format_hours(entry.hours),
                author_username=entry.author_username or "unknown",
                note=entry.note or "",
            )
            for entry in detail.entries
        ),
    )


__all__ = ["serialize_review_detail", "serialize_review_summary"]
