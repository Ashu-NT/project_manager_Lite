"""Change impact serializer."""

from src.core.modules.project_management.api.desktop.scheduling.models.change_impact import (
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


__all__ = ["serialize_change_impact"]
