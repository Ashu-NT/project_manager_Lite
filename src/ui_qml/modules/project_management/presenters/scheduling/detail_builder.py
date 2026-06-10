from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.scheduling import (
    SchedulingCollectionViewModel,
    SchedulingDetailFieldViewModel,
    SchedulingDetailViewModel,
    SchedulingRecordViewModel,
)

from .formatters import constraint_label_for_activity, format_date, int_label


def build_constraints_collection(selected_activity) -> SchedulingCollectionViewModel:
    if selected_activity is None:
        return SchedulingCollectionViewModel(
            title="Constraints",
            subtitle="Schedule controls and date guards for the selected activity.",
            empty_state="Select an activity to inspect schedule constraints and controls.",
        )
    rows: list[SchedulingRecordViewModel] = []
    if selected_activity.start_date:
        rows.append(
            SchedulingRecordViewModel(
                id=f"{selected_activity.id}:start",
                title="Planned Start",
                status_label="Start Control",
                subtitle=format_date(selected_activity.start_date),
                supporting_text="Current start anchor used by the scheduling engine.",
                meta_text="Derived from current plan",
                state={
                    "constraintType": "Planned Start",
                    "constraintValue": format_date(selected_activity.start_date),
                    "constraintStatus": "Current plan",
                },
            )
        )
    if selected_activity.deadline:
        rows.append(
            SchedulingRecordViewModel(
                id=f"{selected_activity.id}:deadline",
                title="Finish No Later Than",
                status_label="Deadline",
                subtitle=format_date(selected_activity.deadline),
                supporting_text="Current deadline control used for delay diagnostics.",
                meta_text="Project deadline guard",
                state={
                    "constraintType": "Finish No Later Than",
                    "constraintValue": format_date(selected_activity.deadline),
                    "constraintStatus": "Active",
                },
            )
        )
    if selected_activity.actual_start:
        rows.append(
            SchedulingRecordViewModel(
                id=f"{selected_activity.id}:actual-start",
                title="Actual Start Lock",
                status_label="Actual",
                subtitle=format_date(selected_activity.actual_start),
                supporting_text="Actual progress constrains forward-pass recalculation.",
                meta_text="Execution lock",
            )
        )
    if selected_activity.actual_end:
        rows.append(
            SchedulingRecordViewModel(
                id=f"{selected_activity.id}:actual-finish",
                title="Actual Finish Lock",
                status_label="Actual",
                subtitle=format_date(selected_activity.actual_end),
                supporting_text="Actual finish constrains recalculation and variance reporting.",
                meta_text="Execution lock",
            )
        )
    return SchedulingCollectionViewModel(
        title="Constraints",
        subtitle="Schedule controls and date guards for the selected activity.",
        items=tuple(rows),
        empty_state="No explicit schedule controls are recorded for the selected activity.",
    )


def build_detail_view_model(
    *,
    selected_activity,
    calendar_label: str,
    dependency_rows,
    resource_load,
    baseline_rows,
) -> SchedulingDetailViewModel:
    if selected_activity is None:
        return SchedulingDetailViewModel(
            title="No activity selected",
            empty_state="Select an activity from the schedule table to inspect logic, constraints, resource pressure, and baseline context.",
        )
    related_resource = resource_load[0] if resource_load else None
    latest_baseline = baseline_rows[0] if baseline_rows else None
    return SchedulingDetailViewModel(
        id=selected_activity.id,
        title=selected_activity.name,
        status_label=(
            "Critical" if selected_activity.is_critical else selected_activity.status_label
        ),
        subtitle=f"{format_date(selected_activity.start_date)} -> {format_date(selected_activity.finish_date)}",
        description=selected_activity.description or "Schedule activity selected for planning inspection.",
        fields=(
            SchedulingDetailFieldViewModel(
                label="Activity ID",
                value=selected_activity.id,
                supporting_text="Current operational identifier.",
            ),
            SchedulingDetailFieldViewModel(
                label="Start",
                value=format_date(selected_activity.start_date),
                supporting_text=f"Latest {format_date(selected_activity.latest_start)}",
            ),
            SchedulingDetailFieldViewModel(
                label="Finish",
                value=format_date(selected_activity.finish_date),
                supporting_text=f"Latest {format_date(selected_activity.latest_finish)}",
            ),
            SchedulingDetailFieldViewModel(
                label="Duration",
                value=int_label(selected_activity.duration_days),
                supporting_text=f"Remaining {int_label(selected_activity.remaining_duration_days)}",
            ),
            SchedulingDetailFieldViewModel(
                label="Float",
                value=int_label(selected_activity.total_float_days),
                supporting_text="Total float in working days.",
            ),
            SchedulingDetailFieldViewModel(
                label="Deadline",
                value=format_date(selected_activity.deadline),
                supporting_text=constraint_label_for_activity(selected_activity),
            ),
            SchedulingDetailFieldViewModel(
                label="Calendar",
                value=calendar_label,
                supporting_text="Current planning calendar.",
            ),
            SchedulingDetailFieldViewModel(
                label="Dependencies",
                value=str(len(dependency_rows)),
                supporting_text="Active predecessor/successor links.",
            ),
            SchedulingDetailFieldViewModel(
                label="Top resource pressure",
                value=related_resource.resource_name if related_resource else "None",
                supporting_text=(
                    related_resource.utilization_label
                    if related_resource
                    else "No resource load data"
                ),
            ),
            SchedulingDetailFieldViewModel(
                label="Latest baseline",
                value=latest_baseline.name if latest_baseline else "None",
                supporting_text=(
                    latest_baseline.created_at_label
                    if latest_baseline
                    else "No baseline stored"
                ),
            ),
        ),
        state={
            "activityId": selected_activity.id,
            "projectId": selected_activity.project_id,
            "title": selected_activity.name,
            "description": selected_activity.description or "",
            "statusLabel": selected_activity.status_label,
            "startDateLabel": format_date(selected_activity.start_date),
            "finishDateLabel": format_date(selected_activity.finish_date),
            "durationLabel": int_label(selected_activity.duration_days),
            "remainingDurationLabel": int_label(selected_activity.remaining_duration_days),
            "floatLabel": int_label(selected_activity.total_float_days),
            "deadlineLabel": format_date(selected_activity.deadline),
            "progressPercent": float(selected_activity.percent_complete or 0.0),
        },
    )


__all__ = ["build_constraints_collection", "build_detail_view_model"]
