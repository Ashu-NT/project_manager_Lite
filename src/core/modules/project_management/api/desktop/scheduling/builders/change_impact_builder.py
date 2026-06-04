"""Change impact view-model assembly."""

from __future__ import annotations
from datetime import date, timedelta

from src.core.modules.project_management.api.desktop.scheduling.models.change_impact import (
    ScheduleImpactAffectedTaskDto,
    ScheduleImpactReportDto,
    SchedulingChangeImpactDto,
)
from src.core.modules.project_management.api.desktop.scheduling.serializers.change_impact_serializer import serialize_change_impact


def build_change_impact(
    project_id: str,
    task_id: str,
    proposed_start: date | None = None,
    proposed_finish: date | None = None,
    proposed_duration_days: int | None = None,
    *,
    change_impact_service=None,
    baseline_service=None,
) -> SchedulingChangeImpactDto | None:
    if not task_id or not project_id or change_impact_service is None:
        return None
    try:
        has_baseline = False
        if baseline_service is not None:
            try:
                has_baseline = baseline_service.get_approved_baseline(project_id) is not None
            except Exception:
                pass
        report = change_impact_service.analyse(
            project_id=project_id,
            changed_task_id=task_id,
            proposed_start=proposed_start,
            proposed_finish=proposed_finish,
            proposed_duration_days=proposed_duration_days,
            has_approved_baseline=has_baseline,
        )
    except Exception:
        return None
    return serialize_change_impact(task_id, report)


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


__all__ = ["build_change_impact", "compute_schedule_impact"]
