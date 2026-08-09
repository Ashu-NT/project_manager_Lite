"""Change impact serializer."""

from src.core.modules.project_management.api.desktop.scheduling.models.change_impact import (
    ScheduleImpactAffectedTaskDto,
    ScheduleImpactReportDto,
    SchedulingChangeImpactAffectedTaskDto,
    SchedulingChangeImpactDto,
)


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
            )
            for impact in report.affected_tasks
        ),
        newly_critical_task_ids=tuple(
            str(task_id) for task_id in report.newly_critical_task_ids
        ),
        no_longer_critical_task_ids=tuple(
            str(task_id) for task_id in report.no_longer_critical_task_ids
        ),
    )


__all__ = ["serialize_change_impact", "serialize_schedule_impact_report"]
