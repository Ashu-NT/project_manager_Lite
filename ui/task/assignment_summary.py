from __future__ import annotations

from core.models import TaskAssignment


TaskAssignmentSummary = dict[str, tuple[int, float, float]]


def build_task_assignment_summary(
    task_ids: list[str],
    assignments: list[TaskAssignment],
) -> TaskAssignmentSummary:
    """Return per-task tuple of (assigned_count, total_alloc_percent, total_hours_logged)."""
    summary: TaskAssignmentSummary = {task_id: (0, 0.0, 0.0) for task_id in task_ids}
    for assignment in assignments:
        task_id = assignment.task_id
        count, alloc, hours = summary.get(task_id, (0, 0.0, 0.0))
        summary[task_id] = (
            count + 1,
            alloc + float(assignment.allocation_percent or 0.0),
            hours + float(assignment.hours_logged or 0.0),
        )
    return summary


__all__ = ["TaskAssignmentSummary", "build_task_assignment_summary"]
