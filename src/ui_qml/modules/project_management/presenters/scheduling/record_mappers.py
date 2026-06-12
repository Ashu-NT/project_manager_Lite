from __future__ import annotations

from datetime import date
from typing import Any

from src.core.modules.project_management.api.desktop import SchedulingConstraintViolationDto
from src.ui_qml.modules.project_management.view_models.scheduling import SchedulingRecordViewModel

from .formatters import (
    constraint_label_for_activity,
    days_between,
    format_date,
    int_label,
    shift_label,
    timeline_bounds,
)

def to_schedule_record(
    item: Any,
    *,
    row_index: int,
    calendar_label: str,
) -> SchedulingRecordViewModel:
    activity_code = f"A-{row_index:03d}"
    progress_value = float(item.percent_complete or 0.0)
    remaining_duration = item.remaining_duration_days
    c_label = constraint_label_for_activity(item)
    late_label = (
        f"Late by {item.late_by_days} day(s)"
        if (item.late_by_days or 0) > 0
        else "On plan"
    )
    return SchedulingRecordViewModel(
        id=item.id,
        title=item.name,
        status_label=item.status_label,
        subtitle=f"Activity {activity_code} | {format_date(item.start_date)} -> {format_date(item.finish_date)}",
        supporting_text=(
            f"Duration {int_label(item.duration_days)} | Remaining {int_label(remaining_duration)} | "
            f"Float {int_label(item.total_float_days)}"
        ),
        meta_text=f"{late_label} | Calendar {calendar_label}",
        state={
            "activityId": item.id,
            "activityCode": activity_code,
            "wbs": f"1.{row_index:02d}",
            "taskName": item.name,
            "startDateLabel": format_date(item.start_date),
            "finishDateLabel": format_date(item.finish_date),
            "durationLabel": int_label(item.duration_days),
            "remainingDurationLabel": int_label(remaining_duration),
            "floatLabel": int_label(item.total_float_days),
            "criticalLabel": "Critical" if item.is_critical else "Normal",
            "constraintLabel": c_label,
            "calendarLabel": calendar_label,
            "progressValue": {
                "value": progress_value / 100.0,
                "label": f"{progress_value:.0f}%",
            },
            "statusLabel": item.status_label,
            "deadlineLabel": format_date(item.deadline),
            "latestStartLabel": format_date(item.latest_start),
            "latestFinishLabel": format_date(item.latest_finish),
            "lateByLabel": int_label(item.late_by_days),
            "actualStartLabel": format_date(item.actual_start),
            "actualFinishLabel": format_date(item.actual_end),
            "description": item.description or "",
        },
    )

def to_timeline_record(item: Any, *, timeline_items: Any) -> SchedulingRecordViewModel:
    bounds = timeline_bounds(timeline_items)
    start_offset = days_between(bounds[0], item.start_date)
    finish_offset = days_between(bounds[0], item.finish_date)
    current_offset = days_between(bounds[0], date.today())
    window_days = (
        max(1, ((bounds[1] - bounds[0]).days + 1))
        if bounds[0] is not None and bounds[1] is not None
        else 1
    )
    span_days = (
        max(1, (finish_offset - start_offset) + 1)
        if start_offset is not None and finish_offset is not None
        else 1
    )
    milestone = bool(
        item.start_date and item.finish_date and item.start_date == item.finish_date
    )
    return SchedulingRecordViewModel(
        id=item.id,
        title=item.name,
        status_label="Critical" if item.is_critical else item.status_label,
        subtitle=f"{format_date(item.start_date)} -> {format_date(item.finish_date)}",
        supporting_text=f"Progress {float(item.percent_complete or 0.0):.0f}% | Float {int_label(item.total_float_days)}",
        meta_text=(
            f"Window {bounds[0].isoformat()} -> {bounds[1].isoformat()}"
            if bounds[0] and bounds[1]
            else ""
        ),
        state={
            "startOffsetDays": start_offset if start_offset is not None else 0,
            "spanDays": span_days,
            "milestone": milestone,
            "critical": bool(item.is_critical),
            "progressPercent": float(item.percent_complete or 0.0),
            "baselinePlaceholder": True,
            "startDateLabel": format_date(item.start_date),
            "finishDateLabel": format_date(item.finish_date),
            "windowStartLabel": format_date(bounds[0]),
            "windowFinishLabel": format_date(bounds[1]),
            "windowDays": window_days,
            "currentOffsetDays": current_offset if current_offset is not None else -1,
        },
    )

def to_critical_path_record(item: Any) -> SchedulingRecordViewModel:
    return SchedulingRecordViewModel(
        id=item.id,
        title=item.name,
        status_label="Critical",
        subtitle=f"{format_date(item.start_date)} -> {format_date(item.finish_date)}",
        supporting_text=f"Float {int_label(item.total_float_days)} | Progress {float(item.percent_complete or 0.0):.0f}%",
        meta_text=f"Latest finish {format_date(item.latest_finish)}",
        state={"activityId": item.id},
    )

def to_delayed_activity_record(item: Any) -> SchedulingRecordViewModel:
    return SchedulingRecordViewModel(
        id=item.id,
        title=item.name,
        status_label="Delayed",
        subtitle=f"Finish {format_date(item.finish_date)} | Deadline {format_date(item.deadline)}",
        supporting_text=f"Late by {int_label(item.late_by_days)} day(s)",
        meta_text=f"Progress {float(item.percent_complete or 0.0):.0f}%",
        state={"activityId": item.id},
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

def to_dependency_record(item: Any) -> SchedulingRecordViewModel:
    return SchedulingRecordViewModel(
        id=item.id,
        title=item.related_activity_name,
        status_label=item.direction_label,
        subtitle=f"{item.dependency_type_label} | Lag {item.lag_days:+d}d",
        supporting_text=item.relationship_label,
        meta_text="Linked activity",
        can_secondary_action=True,
        can_tertiary_action=True,
        state={
            "dependencyId": item.id,
            "taskId": item.related_activity_id,
            "directionLabel": item.direction_label,
            "relatedActivityName": item.related_activity_name,
            "dependencyType": item.dependency_type,
            "dependencyTypeLabel": item.dependency_type_label,
            "lagDays": item.lag_days,
            "lagLabel": f"{item.lag_days:+d}d",
            "relationshipLabel": item.relationship_label,
            "statusLabel": item.status_label,
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
    "to_schedule_record",
    "to_timeline_record",
    "to_critical_path_record",
    "to_delayed_activity_record",
    "to_baseline_compare_record",
    "to_baseline_register_record",
    "to_dependency_record",
    "to_resource_load_record",
    "to_constraint_violation_record",
    "to_baseline_variance_record",
]
