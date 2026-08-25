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
from src.core.modules.project_management.api.desktop.timesheets.models.review import TimesheetReviewDetailDesktopDto
from src.core.modules.project_management.api.desktop.timesheets.services.project_lookup_service import project_names_from_ids
from src.core.modules.project_management.contracts.reads.timesheets import (
    TimesheetReviewInspectorFact,
)


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
        version=int(getattr(row, "version", 1)),
        project_count=int(getattr(row, "project_count", len(row.project_ids))),
        task_count=int(getattr(row, "task_count", 0)),
        generic_entry_count=int(getattr(row, "generic_entry_count", 0)),
        can_approve=bool(getattr(row, "can_approve", False)),
        can_reject=bool(getattr(row, "can_reject", False)),
        can_lock=bool(getattr(row, "can_lock", False)),
        can_unlock=bool(getattr(row, "can_unlock", False)),
    )


def serialize_review_detail(
    detail: TimesheetReviewInspectorFact,
    *,
    project_service,
) -> TimesheetReviewDetailDesktopDto:
    return TimesheetReviewDetailDesktopDto(
        summary=serialize_review_summary(
            detail.summary,
            project_service=project_service,
        ),
    )


__all__ = ["serialize_review_detail", "serialize_review_summary"]
