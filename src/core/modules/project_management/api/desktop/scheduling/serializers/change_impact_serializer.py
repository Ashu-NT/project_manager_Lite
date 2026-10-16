"""Change impact serializer."""

from datetime import date

from src.core.modules.project_management.api.desktop.common.constraint_presentation import (
    constraint_presentation,
)
from src.core.modules.project_management.api.desktop.scheduling.models.change_impact import (
    ScheduleConflictDto,
    ScheduleDriverDto,
    TaskScheduleImpactOverviewDesktopDto,
)
from src.core.modules.project_management.application.scheduling.dto.responses.change_impact import (
    DownstreamExposureDto,
)
from src.core.modules.project_management.application.scheduling.dto.responses.overview import (
    TaskScheduleOverviewResponseDto,
)


def _date_label(value: date | None) -> str:
    return value.isoformat() if value is not None else "--"






def serialize_task_schedule_overview(task_id: str='', overview: TaskScheduleOverviewResponseDto | None=None, *, unavailable_reason: str='') -> TaskScheduleImpactOverviewDesktopDto:
    """Mirrors serialize_schedule_impact_report's ``report=None`` unavailable
    convention -- the desktop API passes ``None`` (never constructs the
    application-layer TaskScheduleOverview itself) when the service isn't
    wired or a lookup fails; this module owns the sole application-object
    construction for the "unavailable" case. ``unavailable_reason`` lets
    the desktop API distinguish "the composition root never wired a
    ScheduleChangeImpactQueryHandler at all" / "the call raised" from the
    per-task reasons TaskScheduleOverview itself reports."""
    if overview is None or not overview.is_available:
        return TaskScheduleImpactOverviewDesktopDto(task_id=overview.task_id if overview is not None else task_id, is_available=False, unavailable_reason=overview.unavailable_reason if overview is not None else unavailable_reason, current_start_label='--', current_finish_label='--', is_critical=False, is_infeasible=False, total_float_days=None, free_float_days=None, baseline_finish_label='--', schedule_variance_days=None, drivers=(), conflicts=(), actual_variances=(), downstream=DownstreamExposureDto(0, 0, 0, 0))
    return TaskScheduleImpactOverviewDesktopDto(task_id=overview.task_id, is_available=True, unavailable_reason='', current_start_label=_date_label(overview.current_start), current_finish_label=_date_label(overview.current_finish), is_critical=bool(overview.is_critical), is_infeasible=bool(overview.is_infeasible), total_float_days=overview.total_float_days, free_float_days=overview.free_float_days, baseline_finish_label=_date_label(overview.baseline_finish), schedule_variance_days=overview.schedule_variance_days, drivers=tuple((ScheduleDriverDto(kind=d.kind, label=constraint_presentation(d.value).label if d.kind == 'constraint' else d.value, detail=d.detail) for d in overview.drivers)), conflicts=tuple((ScheduleConflictDto(task_id=c.task_id, task_name=c.task_name, constraint_type=c.constraint_type, constraint_type_label=constraint_presentation(c.constraint_type).label, constraint_date=c.constraint_date, dependency_required_date=c.dependency_required_date, direction=c.direction, difference_working_days=c.difference_working_days) for c in overview.dependency_conflicts)), actual_variances=overview.actual_variances, downstream=overview.downstream)


__all__ = ['serialize_task_schedule_overview']
