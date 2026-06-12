"""Scheduling desktop API — modular enterprise package."""

from src.core.modules.project_management.api.desktop.scheduling.api import ProjectManagementSchedulingDesktopApi
from src.core.modules.project_management.api.desktop.scheduling.commands.baseline_commands import (
    SchedulingBaselineApproveCommand,
    SchedulingBaselineCreateCommand,
    SchedulingBaselineRejectCommand,
    SchedulingBaselineSubmitCommand,
)
from src.core.modules.project_management.api.desktop.scheduling.commands.calendar_commands import (
    SchedulingCalendarUpdateCommand,
    SchedulingHolidayCreateCommand,
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
from src.core.modules.project_management.api.desktop.scheduling.builders.change_impact_builder import (
    compute_schedule_impact,
)
from src.core.modules.project_management.api.desktop.scheduling.models import (
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
    "SchedulingCalendarUpdateCommand",
    "SchedulingChangeImpactAffectedTaskDto",
    "SchedulingChangeImpactDto",
    "SchedulingConstraintViolationDto",
    "SchedulingDayDescriptor",
    "SchedulingDependencyCreateCommand",
    "SchedulingDependencyDto",
    "SchedulingDependencyTypeDescriptor",
    "SchedulingDependencyUpdateCommand",
    "SchedulingHolidayCreateCommand",
    "SchedulingHolidayDto",
    "SchedulingProjectDependencyDto",
    "SchedulingProjectOptionDescriptor",
    "SchedulingResourceLoadDto",
    "SchedulingTaskDto",
    "SchedulingWorkingDayCalculationCommand",
    "SchedulingWorkingDayCalculationDto",
    "build_project_management_scheduling_desktop_api",
    "compute_schedule_impact",
]
