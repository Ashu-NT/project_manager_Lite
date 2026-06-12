from __future__ import annotations

from typing import Any

from src.ui_qml.modules.project_management.view_models.scheduling import (
    SchedulingCollectionViewModel,
    SchedulingRecordViewModel,
)

from .overview_builder import count_open_ends

def build_diagnostics_collection(
    *,
    schedule_items: Any,
    filtered_schedule: Any,
    dependency_rows: Any,
    resource_load: Any,
) -> SchedulingCollectionViewModel:
    open_ends = count_open_ends(schedule_items, dependency_rows)
    negative_float = sum(
        1 for item in schedule_items if (item.total_float_days or 0) < 0
    )
    delayed = sum(1 for item in filtered_schedule if (item.late_by_days or 0) > 0)
    constraints = sum(
        1
        for item in schedule_items
        if item.deadline is not None and (item.late_by_days or 0) > 0
    )
    overloads = sum(
        1 for item in resource_load if float(item.utilization_percent or 0.0) > 100.0
    )
    rows = (
        SchedulingRecordViewModel(
            id="critical",
            title="Critical Path Length",
            status_label="Critical",
            subtitle=str(sum(1 for item in schedule_items if item.is_critical)),
            supporting_text="Activities on the current zero-float path.",
            meta_text="CPM",
        ),
        SchedulingRecordViewModel(
            id="open-ends",
            title="Open Ends",
            status_label="Warning" if open_ends else "Stable",
            subtitle=str(open_ends),
            supporting_text="Activities missing a predecessor or successor.",
            meta_text="Network quality",
        ),
        SchedulingRecordViewModel(
            id="negative-float",
            title="Negative Float",
            status_label="Danger" if negative_float else "Stable",
            subtitle=str(negative_float),
            supporting_text="Activities with float below zero.",
            meta_text="Schedule pressure",
        ),
        SchedulingRecordViewModel(
            id="delayed",
            title="Delayed Activities",
            status_label="Warning" if delayed else "Stable",
            subtitle=str(delayed),
            supporting_text="Filtered activities already late.",
            meta_text="Execution risk",
        ),
        SchedulingRecordViewModel(
            id="constraints",
            title="Constraint Violations",
            status_label="Danger" if constraints else "Stable",
            subtitle=str(constraints),
            supporting_text="Activities missing their current deadline guard.",
            meta_text="Deadline control",
        ),
        SchedulingRecordViewModel(
            id="overloads",
            title="Resource Conflicts",
            status_label="Danger" if overloads else "Stable",
            subtitle=str(overloads),
            supporting_text="Resources above effective capacity.",
            meta_text="Loading pressure",
        ),
    )
    return SchedulingCollectionViewModel(
        title="Diagnostics",
        subtitle="Planner checks for network quality, float pressure, and resource overload.",
        items=rows,
        empty_state="No diagnostics are available yet.",
    )

__all__ = ["build_diagnostics_collection"]
