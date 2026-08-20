from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import SchedulingConstraintViolationDto
from src.ui_qml.modules.project_management.view_models.scheduling import SchedulingRecordViewModel

from .formatters import (
    format_date,
    int_label,
    shift_label,
)

def to_delayed_activity_record(item: Any) -> SchedulingRecordViewModel:
    return SchedulingRecordViewModel(
        id=item.task_id,
        title=item.name,
        status_label="Delayed",
        subtitle=f"Finish {format_date(item.finish_date)} | Deadline {format_date(item.deadline)}",
        supporting_text=f"Late by {int_label(item.late_by_days)} day(s)",
        meta_text=f"Progress {float(item.percent_complete or 0.0):.0f}%",
        state={"activityId": item.task_id},
    )

def to_baseline_compare_record(item: Any) -> SchedulingRecordViewModel:
    return SchedulingRecordViewModel(
        id=item.task_id,
        title=item.task_name,
        status_label=item.change_type.title(),
        subtitle=(
            f"Start {format_date(item.baseline_a_start)} -> {format_date(item.baseline_b_start)} | "
            f"Finish {format_date(item.baseline_a_finish)} -> {format_date(item.baseline_b_finish)}"
        ),
        supporting_text=(
            f"Start shift {shift_label(item.start_shift_days)} | "
            f"Finish shift {shift_label(item.finish_shift_days)} | "
            f"Duration {shift_label(item.duration_delta_days)}"
        ),
        meta_text=f"Planned cost delta {float(item.planned_cost_delta or 0.0):,.2f}",
        state={
            "taskId": item.task_id,
            "baselineState": item.change_type.title(),
            "createdLabel": "",
            "approvedByLabel": "",
            "varianceState": item.change_type.title(),
        },
    )

def to_baseline_register_record(item: Any) -> SchedulingRecordViewModel:
    return SchedulingRecordViewModel(
        id=item.id,
        title=item.name,
        status_label=item.status_label,
        subtitle=item.created_at_label,
        supporting_text=f"Approved by {item.approved_by_label}",
        meta_text=f"Snapshot {item.variance_state_label}",
        can_primary_action=item.can_submit,
        can_secondary_action=item.can_approve,
        can_tertiary_action=item.can_reject,
        state={
            "baselineId": item.id,
            "baselineName": item.name,
            "createdLabel": item.created_at_label,
            "approvedByLabel": item.approved_by_label,
            "varianceState": item.variance_state_label,
            "status": item.status,
            "statusLabel": item.status_label,
            "canSubmit": item.can_submit,
            "canApprove": item.can_approve,
            "canReject": item.can_reject,
        },
    )

def to_resource_load_record(item: Any) -> SchedulingRecordViewModel:
    return SchedulingRecordViewModel(
        id=item.resource_id,
        title=item.resource_name,
        status_label=item.status_label,
        subtitle=f"Utilization {item.utilization_label} | Capacity {item.capacity_label}",
        supporting_text=f"Peak allocation {item.total_allocation_label} across {item.tasks_count} task(s)",
        meta_text=item.status_label,
        state={
            "resourceId": item.resource_id,
            "resourceName": item.resource_name,
            "allocationLabel": item.total_allocation_label,
            "capacityLabel": item.capacity_label,
            "utilizationLabel": item.utilization_label,
            "tasksCount": item.tasks_count,
            "statusLabel": item.status_label,
        },
    )

def to_constraint_violation_record(
    item: SchedulingConstraintViolationDto,
) -> SchedulingRecordViewModel:
    return SchedulingRecordViewModel(
        id=f"{item.task_id}:{item.constraint_type}",
        title=item.task_name,
        status_label=item.severity_label,
        subtitle=f"{item.constraint_type_label} | Required {item.constraint_date_label}",
        supporting_text=f"Computed {item.computed_date_label} | Overrun {item.overrun_working_days}d",
        meta_text=item.message,
        state={
            "taskId": item.task_id,
            "constraintType": item.constraint_type,
            "constraintTypeLabel": item.constraint_type_label,
            "constraintDateLabel": item.constraint_date_label,
            "computedDateLabel": item.computed_date_label,
            "overrunDays": item.overrun_working_days,
            "severity": item.severity,
            "severityLabel": item.severity_label,
            "message": item.message,
        },
    )

def to_baseline_variance_record(rec: Any) -> SchedulingRecordViewModel:
    task_name = str(
        getattr(rec, "task_name", "") or getattr(rec, "task_id", "") or "Unknown"
    )
    start_var = int(getattr(rec, "start_variance_days", 0) or 0)
    finish_var = int(getattr(rec, "finish_variance_days", 0) or 0)
    cost_var = float(getattr(rec, "cost_variance", 0.0) or 0.0)
    created = getattr(rec, "created_at", None)
    if start_var > 0 or finish_var > 0:
        status = "Delayed"
    elif start_var < 0 or finish_var < 0:
        status = "Ahead"
    else:
        status = "Shifted"
    return SchedulingRecordViewModel(
        id=str(getattr(rec, "id", "") or ""),
        title=task_name,
        status_label=status,
        subtitle=f"Start {shift_label(start_var)} | Finish {shift_label(finish_var)}",
        supporting_text=f"Cost delta {cost_var:+,.2f}",
        meta_text=format_date(created) if created else "-",
        state={
            "taskId": str(getattr(rec, "task_id", "") or ""),
            "taskName": task_name,
            "startVarianceDays": start_var,
            "startVarianceDaysLabel": shift_label(start_var),
            "finishVarianceDays": finish_var,
            "finishVarianceDaysLabel": shift_label(finish_var),
            "costVariance": cost_var,
            "costVarianceLabel": f"{cost_var:+,.2f}",
            "createdLabel": format_date(created) if created else "-",
        },
    )

__all__ = [
    "to_delayed_activity_record",
    "to_baseline_compare_record",
    "to_baseline_register_record",
    "to_resource_load_record",
    "to_constraint_violation_record",
    "to_baseline_variance_record",
]
