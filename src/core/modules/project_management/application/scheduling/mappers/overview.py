"""Map canonical schedule facts without formatting dates or constraints."""

from src.core.modules.project_management.application.scheduling.dto.responses.change_impact import (
    ActualVarianceDto,
    DownstreamExposureDto,
)
from src.core.modules.project_management.application.scheduling.dto.responses.overview import (
    ScheduleConflictResponseDto,
    ScheduleDriverResponseDto,
    TaskScheduleOverviewResponseDto,
)
from src.core.modules.project_management.application.scheduling.forecasting.task_schedule_overview import (
    TaskScheduleOverview,
)


def map_schedule_overview(overview: TaskScheduleOverview) -> TaskScheduleOverviewResponseDto:
    return TaskScheduleOverviewResponseDto(
        task_id=overview.task_id, is_available=overview.is_available,
        unavailable_reason=overview.unavailable_reason, current_start=overview.current_start,
        current_finish=overview.current_finish, is_critical=overview.is_critical,
        is_infeasible=overview.is_infeasible, total_float_days=overview.total_float_days,
        free_float_days=overview.free_float_days, baseline_finish=overview.baseline_finish,
        schedule_variance_days=overview.schedule_variance_days,
        drivers=tuple(ScheduleDriverResponseDto(kind=d.kind, value=d.label, detail=d.detail) for d in overview.drivers),
        dependency_conflicts=tuple(ScheduleConflictResponseDto(
            task_id=c.task_id, task_name=c.task_name, constraint_type=c.constraint_type.value,
            constraint_date=c.constraint_date, dependency_required_date=c.dependency_required_date,
            direction=c.direction, difference_working_days=c.difference_working_days,
        ) for c in overview.dependency_conflicts),
        actual_variances=tuple(ActualVarianceDto(
            task_id=v.task_id, task_name=v.task_name, direction=v.direction,
            actual_date=v.actual_date, dependency_required_date=v.dependency_required_date,
            difference_working_days=v.difference_working_days,
        ) for v in overview.actual_variances),
        downstream=DownstreamExposureDto(
            direct_successor_count=overview.downstream.direct_successor_count,
            downstream_task_count=overview.downstream.downstream_task_count,
            downstream_milestone_count=overview.downstream.downstream_milestone_count,
            critical_downstream_count=overview.downstream.critical_downstream_count,
        ),
    )
