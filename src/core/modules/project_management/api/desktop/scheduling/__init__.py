"""Scheduling desktop API — modular enterprise package."""

from src.core.modules.project_management.api.desktop.scheduling.api import ProjectManagementSchedulingDesktopApi
from src.core.modules.project_management.api.desktop.scheduling.commands.baseline_commands import (
    SchedulingBaselineApproveCommand,
    SchedulingBaselineCreateCommand,
    SchedulingBaselineRejectCommand,
    SchedulingBaselineSubmitCommand,
)
from src.core.modules.project_management.api.desktop.scheduling.commands.dependency_commands import (
    SchedulingDependencyCreateCommand,
    SchedulingDependencyUpdateCommand,
)
from src.core.modules.project_management.api.desktop.scheduling.commands.working_day_commands import (
    SchedulingWorkingDayCalculationCommand,
)
from src.core.modules.project_management.api.desktop.scheduling.factories.scheduling_api_factory import (
    build_project_management_scheduling_desktop_api,
)
from src.core.modules.project_management.api.desktop.scheduling.models import (
    ActualVarianceDto,
    DownstreamExposureDto,
    ScheduleConflictDto,
    ScheduleDriverDto,
    TaskScheduleImpactOverviewDesktopDto,
    ScheduleImpactAffectedTaskDto,
    ScheduleImpactReportDto,
    SchedulingBaselineComparisonRowDto,
    SchedulingBaselineOptionDescriptor,
    SchedulingBaselineRowDto,
    SchedulingBaselineVarianceRowDto,
    SchedulingCalendarOptionDescriptor,
    SchedulingCalendarSnapshotDto,
    SchedulingChangeImpactAffectedTaskDto,
    SchedulingChangeImpactDto,
    SchedulingConstraintViolationDto,
    SchedulingDayDescriptor,
    SchedulingDependencyDto,
    SchedulingDependencyTypeDescriptor,
    SchedulingHolidayDto,
    SchedulingProjectDependencyDto,
    SchedulingProjectOptionDescriptor,
    SchedulingResourceLoadDto,
    SchedulingTaskDto,
    SchedulingWorkingDayCalculationDto,
)

__all__ = [
    "ProjectManagementSchedulingDesktopApi",
    "ActualVarianceDto",
    "DownstreamExposureDto",
    "ScheduleConflictDto",
    "ScheduleDriverDto",
    "TaskScheduleImpactOverviewDesktopDto",
    "ScheduleImpactAffectedTaskDto",
    "ScheduleImpactReportDto",
    "SchedulingBaselineApproveCommand",
    "SchedulingBaselineComparisonRowDto",
    "SchedulingBaselineCreateCommand",
    "SchedulingBaselineOptionDescriptor",
    "SchedulingBaselineRejectCommand",
    "SchedulingBaselineRowDto",
    "SchedulingBaselineSubmitCommand",
    "SchedulingBaselineVarianceRowDto",
    "SchedulingCalendarOptionDescriptor",
    "SchedulingCalendarSnapshotDto",
    "SchedulingChangeImpactAffectedTaskDto",
    "SchedulingChangeImpactDto",
    "SchedulingConstraintViolationDto",
    "SchedulingDayDescriptor",
    "SchedulingDependencyCreateCommand",
    "SchedulingDependencyDto",
    "SchedulingDependencyTypeDescriptor",
    "SchedulingDependencyUpdateCommand",
    "SchedulingHolidayDto",
    "SchedulingProjectDependencyDto",
    "SchedulingProjectOptionDescriptor",
    "SchedulingResourceLoadDto",
    "SchedulingTaskDto",
    "SchedulingWorkingDayCalculationCommand",
    "SchedulingWorkingDayCalculationDto",
    "build_project_management_scheduling_desktop_api",
]
