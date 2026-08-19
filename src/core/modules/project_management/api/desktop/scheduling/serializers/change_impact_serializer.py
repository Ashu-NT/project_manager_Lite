"""Change impact serializer."""

from src.core.modules.project_management.api.desktop.scheduling.models.change_impact import (
    ActualVarianceDto,
    DownstreamExposureDto,
    ScheduleConflictDto,
    ScheduleDriverDto,
    ScheduleImpactAffectedTaskDto,
    ScheduleImpactReportDto,
    SchedulingChangeImpactAffectedTaskDto,
    SchedulingChangeImpactDto,
    TaskScheduleImpactOverviewDesktopDto,
)


def _date_label(value) -> str:
    return value.isoformat() if value is not None else "--"


def serialize_change_impact(task_id: str, report) -> SchedulingChangeImpactDto:
    return SchedulingChangeImpactDto(
        task_id=task_id,
        affected_count=int(report.max_project_finish_shift_days != 0) + len(report.affected_tasks),
        max_project_finish_shift_days=int(report.max_project_finish_shift_days or 0),
        requires_approval=bool(report.requires_approval),
        newly_critical_count=len(report.newly_critical_task_ids or []),
        no_longer_critical_count=len(report.no_longer_critical_task_ids or []),
        affected_tasks=tuple(
            SchedulingChangeImpactAffectedTaskDto(
                task_id=str(t.task_id or ""),
                task_name=str(getattr(t, "task_name", t.task_id) or t.task_id or "Task"),
                start_shift_days=int(getattr(t, "start_shift_days", 0) or 0),
                finish_shift_days=int(getattr(t, "finish_shift_days", 0) or 0),
                is_critical=bool(getattr(t, "is_critical", False)),
            )
            for t in (report.affected_tasks or [])[:20]
        ),
    )


def serialize_schedule_impact_report(
    *,
    task_id: str,
    project_id: str,
    simulated_delay_days: int,
    report=None,
) -> ScheduleImpactReportDto:
    if report is None:
        return ScheduleImpactReportDto(
            task_id=task_id,
            project_id=project_id,
            is_available=False,
            simulated_delay_days=simulated_delay_days,
            affected_count=0,
            max_project_finish_shift_days=0,
            requires_approval=False,
            affected_tasks=(),
            newly_critical_task_ids=(),
            no_longer_critical_task_ids=(),
        )
    return ScheduleImpactReportDto(
        task_id=task_id,
        project_id=project_id,
        is_available=True,
        simulated_delay_days=simulated_delay_days,
        affected_count=len(report.affected_tasks),
        max_project_finish_shift_days=int(report.max_project_finish_shift_days or 0),
        requires_approval=bool(report.requires_approval),
        affected_tasks=tuple(
            ScheduleImpactAffectedTaskDto(
                task_id=str(impact.task_id or ""),
                task_name=str(impact.task_name or ""),
                original_start=impact.original_start,
                original_finish=impact.original_finish,
                proposed_start=impact.proposed_start,
                proposed_finish=impact.proposed_finish,
                start_shift_days=int(impact.start_shift_days or 0),
                finish_shift_days=int(impact.finish_shift_days or 0),
                is_critical=bool(impact.is_critical),
                is_milestone=bool(getattr(impact, "is_milestone", False)),
            )
            for impact in report.affected_tasks
        ),
        newly_critical_task_ids=tuple(
            str(task_id) for task_id in report.newly_critical_task_ids
        ),
        no_longer_critical_task_ids=tuple(
            str(task_id) for task_id in report.no_longer_critical_task_ids
        ),
        critical_path_changed=bool(getattr(report, "critical_path_changed", False)),
        conflict_count=len(getattr(report, "dependency_conflicts", None) or []),
        blocked_by_deadline=bool(getattr(report, "blocked_by_deadline", False)),
        blocked_reason=str(getattr(report, "blocked_reason", "") or ""),
    )


def serialize_task_schedule_overview(
    task_id: str = "",
    overview=None,
    *,
    unavailable_reason: str = "",
) -> TaskScheduleImpactOverviewDesktopDto:
    """Mirrors serialize_schedule_impact_report's ``report=None`` unavailable
    convention -- the desktop API passes ``None`` (never constructs the
    application-layer TaskScheduleOverview itself) when the service isn't
    wired or a lookup fails; this module owns the sole application-object
    construction for the "unavailable" case. ``unavailable_reason`` lets
    the desktop API distinguish "the composition root never wired a
    ScheduleChangeImpactService at all" / "the call raised" from the
    per-task reasons TaskScheduleOverview itself reports."""
    if overview is None or not overview.is_available:
        return TaskScheduleImpactOverviewDesktopDto(
            task_id=(overview.task_id if overview is not None else task_id),
            is_available=False,
            unavailable_reason=(
                overview.unavailable_reason if overview is not None else unavailable_reason
            ),
            current_start_label="--",
            current_finish_label="--",
            is_critical=False,
            total_float_days=None,
            free_float_days=None,
            baseline_finish_label="--",
            schedule_variance_days=None,
            drivers=(),
            conflicts=(),
            actual_variances=(),
            downstream=DownstreamExposureDto(0, 0, 0, 0),
        )
    return TaskScheduleImpactOverviewDesktopDto(
        task_id=overview.task_id,
        is_available=True,
        unavailable_reason="",
        current_start_label=_date_label(overview.current_start),
        current_finish_label=_date_label(overview.current_finish),
        is_critical=bool(overview.is_critical),
        total_float_days=overview.total_float_days,
        free_float_days=overview.free_float_days,
        baseline_finish_label=_date_label(overview.baseline_finish),
        schedule_variance_days=overview.schedule_variance_days,
        drivers=tuple(
            ScheduleDriverDto(kind=d.kind, label=d.label, detail=d.detail)
            for d in overview.drivers
        ),
        conflicts=tuple(
            ScheduleConflictDto(
                task_id=c.task_id,
                task_name=c.task_name,
                constraint_type=c.constraint_type.value,
                constraint_date=c.constraint_date,
                dependency_required_date=c.dependency_required_date,
                direction=c.direction,
                difference_working_days=c.difference_working_days,
            )
            for c in overview.dependency_conflicts
        ),
        actual_variances=tuple(
            ActualVarianceDto(
                task_id=v.task_id,
                task_name=v.task_name,
                direction=v.direction,
                actual_date=v.actual_date,
                dependency_required_date=v.dependency_required_date,
                difference_working_days=v.difference_working_days,
            )
            for v in overview.actual_variances
        ),
        downstream=DownstreamExposureDto(
            direct_successor_count=overview.downstream.direct_successor_count,
            downstream_task_count=overview.downstream.downstream_task_count,
            downstream_milestone_count=overview.downstream.downstream_milestone_count,
            critical_downstream_count=overview.downstream.critical_downstream_count,
        ),
    )


__all__ = [
    "serialize_change_impact",
    "serialize_schedule_impact_report",
    "serialize_task_schedule_overview",
]
