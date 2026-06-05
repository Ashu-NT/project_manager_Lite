"""Timesheets desktop API package."""

from src.core.modules.project_management.api.desktop.timesheets.api import (
    ProjectManagementTimesheetsDesktopApi,
)
from src.core.modules.project_management.api.desktop.timesheets.commands.entry_commands import (
    TimesheetEntryCreateCommand,
    TimesheetEntryUpdateCommand,
)
from src.core.modules.project_management.api.desktop.timesheets.factories.timesheets_api_factory import (
    build_project_management_timesheets_desktop_api,
)
from src.core.modules.project_management.api.desktop.timesheets.models.entries import (
    TimesheetEntryDesktopDto,
)
from src.core.modules.project_management.api.desktop.timesheets.models.options import (
    TimesheetAssignmentOptionDescriptor,
    TimesheetOptionDescriptor,
    TimesheetPeriodOptionDescriptor,
    TimesheetProjectOptionDescriptor,
)
from src.core.modules.project_management.api.desktop.timesheets.models.periods import (
    TimesheetPeriodSummaryDesktopDto,
)
from src.core.modules.project_management.api.desktop.timesheets.models.review import (
    TimesheetReviewDetailDesktopDto,
    TimesheetReviewEntryDesktopDto,
)
from src.core.modules.project_management.api.desktop.timesheets.models.snapshots import (
    TimesheetAssignmentSnapshotDesktopDto,
)

__all__ = [
    "ProjectManagementTimesheetsDesktopApi",
    "TimesheetAssignmentOptionDescriptor",
    "TimesheetAssignmentSnapshotDesktopDto",
    "TimesheetEntryCreateCommand",
    "TimesheetEntryDesktopDto",
    "TimesheetEntryUpdateCommand",
    "TimesheetOptionDescriptor",
    "TimesheetPeriodOptionDescriptor",
    "TimesheetPeriodSummaryDesktopDto",
    "TimesheetProjectOptionDescriptor",
    "TimesheetReviewDetailDesktopDto",
    "TimesheetReviewEntryDesktopDto",
    "build_project_management_timesheets_desktop_api",
]
