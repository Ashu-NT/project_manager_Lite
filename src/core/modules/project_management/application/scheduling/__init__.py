"""Scheduling use cases — re-exports all public API for backward compatibility."""

from src.core.modules.project_management.application.scheduling.baselines import (
    BaselineComparisonQueryHandler,
    BaselineComparisonReport,
    BaselineQueryHandler,
    TaskVariance,
)
from src.core.modules.project_management.application.scheduling.calendars import (
    BoundProjectCalendar,
    ProjectCalendarAdapter,
)
from src.core.modules.project_management.application.scheduling.cpm import (
    ConstraintType,
    ConstraintValidationResult,
    ConstraintValidator,
    ConstraintViolation,
    CPMResult,
    build_project_dependency_graph,
    build_schedule_result,
    run_backward_pass,
    run_cpm,
    run_forward_pass,
)
from src.core.modules.project_management.application.scheduling.forecasting import (
    ScheduleChangeImpactQueryHandler,
    ScheduleChangeImpactReport,
    TaskImpact,
)
from src.core.modules.project_management.application.scheduling.leveling import (
    ResourceLevelingPlanner,
)
from src.core.modules.project_management.application.scheduling.models import (
    CPMTaskInfo,
    ResourceConflict,
    ResourceConflictEntry,
)
from src.core.modules.project_management.application.scheduling.services import (
    SchedulingEngine,
)
from src.core.platform.application.time_management.calendar.capacity.global_calendar_shim import (
    GlobalCalendarShim,
)
from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)

__all__ = [
    "BaselineComparisonReport",
    "BaselineComparisonQueryHandler",
    "BaselineQueryHandler",
    "BoundProjectCalendar",
    "CPMResult",
    "CPMTaskInfo",
    "CalendarProtocol",
    "ConstraintType",
    "ConstraintValidationResult",
    "ConstraintValidator",
    "ConstraintViolation",
    "GlobalCalendarShim",
    "ProjectCalendarAdapter",
    "ResourceConflict",
    "ResourceConflictEntry",
    "ResourceLevelingPlanner",
    "ScheduleChangeImpactReport",
    "ScheduleChangeImpactQueryHandler",
    "SchedulingEngine",
    "TaskImpact",
    "TaskVariance",
    "build_project_dependency_graph",
    "build_schedule_result",
    "run_backward_pass",
    "run_cpm",
    "run_forward_pass",
]
