from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.scheduling import (
    SchedulingMetricViewModel,
    SchedulingOverviewViewModel,
)


def count_open_ends(schedule_items, dependency_rows) -> int:
    if not schedule_items:
        return 0
    predecessor_count: dict[str, int] = {}
    successor_count: dict[str, int] = {}
    for row in dependency_rows:
        successor_count[row.predecessor_task_id] = (
            successor_count.get(row.predecessor_task_id, 0) + 1
        )
        predecessor_count[row.successor_task_id] = (
            predecessor_count.get(row.successor_task_id, 0) + 1
        )
    open_ends = 0
    for item in schedule_items:
        if predecessor_count.get(item.id, 0) == 0 or successor_count.get(item.id, 0) == 0:
            open_ends += 1
    return open_ends


def build_overview(
    *,
    resolved_project_id: str,
    schedule_items,
    filtered_schedule,
    critical_items,
    delayed_items,
    dependency_rows,
    baseline_rows,
    calendar_snapshot,
    resource_load,
) -> SchedulingOverviewViewModel:
    open_ends = count_open_ends(schedule_items, dependency_rows)
    negative_float = sum(
        1 for item in schedule_items if (item.total_float_days or 0) < 0
    )
    overloaded_resources = sum(
        1 for item in resource_load if float(item.utilization_percent or 0.0) > 100.0
    )
    return SchedulingOverviewViewModel(
        title="Scheduling",
        subtitle=(
            "Enterprise planning console for activities, CPM diagnostics, baselines, and resource pressure."
            if resolved_project_id
            else "Select a project to review schedule control, baselines, and resource pressure."
        ),
        metrics=(
            SchedulingMetricViewModel(
                label="Activities",
                value=str(len(filtered_schedule)),
                supporting_text=f"{len(schedule_items)} loaded",
            ),
            SchedulingMetricViewModel(
                label="Critical",
                value=str(len(critical_items)),
                supporting_text="Zero-float path",
            ),
            SchedulingMetricViewModel(
                label="Delayed",
                value=str(len(delayed_items)),
                supporting_text="Activities already late",
            ),
            SchedulingMetricViewModel(
                label="Open ends",
                value=str(open_ends),
                supporting_text="Missing predecessor/successor",
            ),
            SchedulingMetricViewModel(
                label="Neg. float",
                value=str(negative_float),
                supporting_text="Activities with float below zero",
            ),
            SchedulingMetricViewModel(
                label="Baselines",
                value=str(len(baseline_rows)),
                supporting_text="Stored schedule freezes",
            ),
            SchedulingMetricViewModel(
                label="Calendar",
                value=f"{float(calendar_snapshot.hours_per_day or 0.0):g}h",
                supporting_text=f"{len(calendar_snapshot.holidays)} holiday(s)",
            ),
            SchedulingMetricViewModel(
                label="Overloads",
                value=str(overloaded_resources),
                supporting_text="Resources above capacity",
            ),
        ),
    )


__all__ = ["count_open_ends", "build_overview"]
