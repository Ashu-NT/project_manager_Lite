"""Scheduling use cases — re-exports all public API for backward compatibility."""

from src.core.modules.project_management.application.scheduling.baselines import (
    BaselineComparisonReport,
    BaselineComparisonService,
    BaselineService,
    TaskVariance,
)
from src.core.modules.project_management.application.scheduling.calendars import (
    BoundProjectCalendar,
    CalendarService,
    ProjectCalendarAdapter,
)
from src.core.modules.project_management.application.scheduling.cpm import (
    CPMCalculator,
    CPMResult,
    ConstraintType,
    ConstraintValidationResult,
    ConstraintValidator,
    ConstraintViolation,
    build_project_dependency_graph,
    build_schedule_result,
    run_backward_pass,
    run_forward_pass,
)
from src.core.modules.project_management.application.scheduling.dependencies import (
    DependencyDateResult,
    DependencyResolver,
)
from src.core.modules.project_management.application.scheduling.forecasting import (
    ScheduleChangeImpactReport,
    ScheduleChangeImpactService,
    TaskImpact,
)
from src.core.modules.project_management.application.scheduling.leveling import (
    ResourceLevelingEngine,
    ResourceLevelingMixin,
)
from src.core.modules.project_management.application.scheduling.models import (
    CPMTaskInfo,
    ResourceConflict,
    ResourceConflictEntry,
    ResourceLevelingAction,
    ResourceLevelingResult,
)
from src.core.modules.project_management.application.scheduling.services import SchedulingEngine
from src.core.platform.calendar.application.calendar_protocol import CalendarProtocol
from src.core.platform.calendar.application.global_calendar_shim import GlobalCalendarShim

__all__ = [
    # Models
    "CPMTaskInfo",
    "ResourceConflict",
    "ResourceConflictEntry",
    "ResourceLevelingAction",
    "ResourceLevelingResult",
    # CPM
    "CPMCalculator",
    "CPMResult",
    "ConstraintType",
    "ConstraintValidationResult",
    "ConstraintValidator",
    "ConstraintViolation",
    "build_project_dependency_graph",
    "build_schedule_result",
    "run_backward_pass",
    "run_forward_pass",
    # Dependencies
    "DependencyDateResult",
    "DependencyResolver",
    # Leveling
    "ResourceLevelingEngine",
    "ResourceLevelingMixin",
    # Calendars
    "BoundProjectCalendar",
    "CalendarService",
    "ProjectCalendarAdapter",
    # Baselines
    "BaselineComparisonReport",
    "BaselineComparisonService",
    "BaselineService",
    "TaskVariance",
    # Forecasting
    "ScheduleChangeImpactReport",
    "ScheduleChangeImpactService",
    "TaskImpact",
    # Main service
    "SchedulingEngine",
    # Platform re-exports (kept for backward compat)
    "CalendarProtocol",
    "GlobalCalendarShim",
]
