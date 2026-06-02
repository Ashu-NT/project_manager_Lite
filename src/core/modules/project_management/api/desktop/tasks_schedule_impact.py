from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class ScheduleImpactAffectedTaskDto:
    task_id: str
    task_name: str
    original_start: date | None
    original_finish: date | None
    proposed_start: date | None
    proposed_finish: date | None
    start_shift_days: int
    finish_shift_days: int
    is_critical: bool


@dataclass(frozen=True)
class ScheduleImpactReportDto:
    task_id: str
    project_id: str
    is_available: bool
    simulated_delay_days: int
    affected_count: int
    max_project_finish_shift_days: int
    requires_approval: bool
    affected_tasks: tuple[ScheduleImpactAffectedTaskDto, ...]
    newly_critical_task_ids: tuple[str, ...]
    no_longer_critical_task_ids: tuple[str, ...]


def compute_schedule_impact(
    task_id: str,
    project_id: str,
    *,
    task_service,
    schedule_change_impact_service,
) -> ScheduleImpactReportDto:
    normalized_task_id = (task_id or "").strip()
    normalized_project_id = (project_id or "").strip()
    _empty = ScheduleImpactReportDto(
        task_id=normalized_task_id,
        project_id=normalized_project_id,
        is_available=False,
        simulated_delay_days=1,
        affected_count=0,
        max_project_finish_shift_days=0,
        requires_approval=False,
        affected_tasks=(),
        newly_critical_task_ids=(),
        no_longer_critical_task_ids=(),
    )
    if not normalized_task_id or not normalized_project_id:
        return _empty
    if schedule_change_impact_service is None or task_service is None:
        return _empty
    try:
        task = task_service.get_task(normalized_task_id)
    except Exception:
        return _empty
    if task is None or task.start_date is None:
        return _empty
    try:
        proposed_start = task.start_date + timedelta(days=1)
        report = schedule_change_impact_service.analyse(
            project_id=normalized_project_id,
            changed_task_id=normalized_task_id,
            proposed_start=proposed_start,
            has_approved_baseline=False,
        )
    except Exception:
        return _empty
    return ScheduleImpactReportDto(
        task_id=normalized_task_id,
        project_id=normalized_project_id,
        is_available=True,
        simulated_delay_days=1,
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
            )
            for impact in report.affected_tasks
        ),
        newly_critical_task_ids=tuple(str(tid) for tid in report.newly_critical_task_ids),
        no_longer_critical_task_ids=tuple(str(tid) for tid in report.no_longer_critical_task_ids),
    )


__all__ = [
    "ScheduleImpactAffectedTaskDto",
    "ScheduleImpactReportDto",
    "compute_schedule_impact",
]
