from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop.common.constraint_presentation import (
    constraint_presentation,
)
from src.core.modules.project_management.application.dashboard.models.report_models import (
    ResourceLoadRow,
)
from src.core.modules.project_management.application.scheduling.cpm.constraint_validator import (
    ConstraintViolation,
)
from src.core.modules.project_management.application.scheduling.dto.responses.baselines import (
    SchedulingBaselineComparisonRowDto,
    SchedulingBaselineResponse,
    SchedulingBaselineVarianceRowDto,
)
from src.ui_qml.modules.project_management.view_models.scheduling import (
    SchedulingRecordViewModel,
)

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

def to_baseline_compare_record(item: SchedulingBaselineComparisonRowDto) -> SchedulingRecordViewModel:
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
        meta_text=f"Planned cost delta {item.planned_cost_delta:,.2f}",
        state={
            "taskId": item.task_id,
            "baselineState": item.change_type.title(),
            "createdLabel": "",
            "approvedByLabel": "",
            "varianceState": item.change_type.title(),
        },
    )

def to_baseline_register_record(item: SchedulingBaselineResponse, index: int = 0) -> SchedulingRecordViewModel:
    created_at_label = item.created_at.strftime("%Y-%m-%d %H:%M")
    approved_by_label = str(item.approved_by or "System snapshot")
    variance_state_label = "Latest" if index == 0 else "Stored"
    status_label = item.status.replace("_", " ").title()
    return SchedulingRecordViewModel(
        id=item.id,
        title=item.name,
        status_label=status_label,
        subtitle=created_at_label,
        supporting_text=f"Approved by {approved_by_label}",
        meta_text=f"Snapshot {variance_state_label}",
        can_primary_action=item.can_submit,
        can_secondary_action=item.can_approve,
        can_tertiary_action=item.can_reject,
        state={
            "baselineId": item.id,
            "baselineName": item.name,
            "createdLabel": created_at_label,
            "approvedByLabel": approved_by_label,
            "varianceState": variance_state_label,
            "status": item.status,
            "statusLabel": status_label,
            "canSubmit": item.can_submit,
            "canApprove": item.can_approve,
            "canReject": item.can_reject,
        },
    )

def to_resource_load_record(item: ResourceLoadRow) -> SchedulingRecordViewModel:
    allocation_label = f"{item.total_allocation_percent:.1f}%"
    capacity_label = f"{item.capacity_percent:.1f}%"
    utilization_label = f"{item.utilization_percent:.1f}%"
    status_label = item.utilization_status_label
    return SchedulingRecordViewModel(
        id=item.resource_id,
        title=item.resource_name,
        status_label=status_label,
        subtitle=f"Utilization {utilization_label} | Capacity {capacity_label}",
        supporting_text=f"Peak allocation {allocation_label} across {item.tasks_count} task(s)",
        meta_text=status_label,
        state={
            "resourceId": item.resource_id,
            "resourceName": item.resource_name,
            "allocationLabel": allocation_label,
            "capacityLabel": capacity_label,
            "utilizationLabel": utilization_label,
            "tasksCount": item.tasks_count,
            "statusLabel": status_label,
        },
    )

def to_constraint_violation_record(
    item: ConstraintViolation,
) -> SchedulingRecordViewModel:
    constraint_type = item.constraint_type.value
    constraint_label = constraint_presentation(item.constraint_type).label
    constraint_date_label = item.constraint_date.isoformat() if item.constraint_date else "-"
    computed_date_label = item.computed_date.isoformat() if item.computed_date else "-"
    severity = "hard" if item.is_hard else "soft"
    severity_label = "Hard Constraint" if item.is_hard else "Soft Constraint"
    return SchedulingRecordViewModel(
        id=f"{item.task_id}:{constraint_type}",
        title=item.task_name,
        status_label=severity_label,
        subtitle=f"{constraint_label} | Required {constraint_date_label}",
        supporting_text=f"Computed {computed_date_label} | Overrun {item.overrun_working_days}d",
        meta_text=item.message,
        state={
            "taskId": item.task_id,
            "constraintType": constraint_type,
            "constraintTypeLabel": constraint_label,
            "constraintDateLabel": constraint_date_label,
            "computedDateLabel": computed_date_label,
            "overrunDays": item.overrun_working_days,
            "severity": severity,
            "severityLabel": severity_label,
            "message": item.message,
        },
    )

def to_baseline_variance_record(rec: SchedulingBaselineVarianceRowDto) -> SchedulingRecordViewModel:
    task_name = rec.task_name or rec.task_id or "Unknown"
    start_var = rec.start_variance_days
    finish_var = rec.finish_variance_days
    cost_var = rec.cost_variance
    created = rec.created_at
    if start_var > 0 or finish_var > 0:
        status = "Delayed"
    elif start_var < 0 or finish_var < 0:
        status = "Ahead"
    else:
        status = "Shifted"
    return SchedulingRecordViewModel(
        id=rec.id,
        title=task_name,
        status_label=status,
        subtitle=f"Start {shift_label(start_var)} | Finish {shift_label(finish_var)}",
        supporting_text=f"Cost delta {cost_var:+,.2f}",
        meta_text=format_date(created) if created else "-",
        state={
            "taskId": rec.task_id,
            "taskName": task_name,
            "startVarianceDays": start_var,
            "startVarianceDaysLabel": shift_label(start_var),
            "finishVarianceDays": finish_var,
            "finishVarianceDaysLabel": shift_label(finish_var),
            "costVariance": float(cost_var),
            "costVarianceLabel": f"{cost_var:+,.2f}",
            "createdLabel": format_date(created) if created else "-",
        },
    )

__all__ = [
    "to_baseline_compare_record",
    "to_baseline_register_record",
    "to_baseline_variance_record",
    "to_constraint_violation_record",
    "to_delayed_activity_record",
    "to_resource_load_record",
]
