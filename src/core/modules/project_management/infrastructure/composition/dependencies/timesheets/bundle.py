from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.application.timesheets import (
    TimesheetReviewQueryHandler,
    TimesheetWorkspaceCommandHandler,
    TimesheetWorkspaceQueryHandler,
)
from src.core.platform.application.time_management.time import (
    TimeEntryCommandHandler,
    TimeEntryQueryHandler,
    TimesheetPeriodQueryHandler,
    TimesheetPeriodTransitionHandler,
)


@dataclass(frozen=True)
class TimesheetComposition:
    workspace_queries: TimesheetWorkspaceQueryHandler
    workspace_commands: TimesheetWorkspaceCommandHandler
    review_queries: TimesheetReviewQueryHandler
    time_entries: TimeEntryCommandHandler
    period_transitions: TimesheetPeriodTransitionHandler
    time_entry_queries: TimeEntryQueryHandler
    period_queries: TimesheetPeriodQueryHandler
