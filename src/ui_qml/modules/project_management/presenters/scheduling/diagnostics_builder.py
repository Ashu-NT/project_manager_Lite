from __future__ import annotations

from typing import Any

from src.ui_qml.modules.project_management.view_models.scheduling import (
    SchedulingCollectionViewModel,
    SchedulingRecordViewModel,
)

def build_diagnostics_collection(
    *,
    schedule_items: Any,
    filtered_schedule: Any,
    dependency_rows: Any,
    resource_load: Any,
) -> SchedulingCollectionViewModel:
    # Critical/Open-ends/Infeasible/Delayed/Overloads are already reported by
    # the Overview KPI strip (overview_builder.build_overview) -- this
    # collection only carries the one diagnostic the KPI strip does not:
    # deadline breaches. Deadline lateness is not itself a constraint type,
    # so this row is titled/labeled distinctly from the real per-constraint-
    # type "Constraint Overruns" table below it in
    # SchedulingDiagnosticsPanel.qml.
    constraints = sum(
        1
        for item in schedule_items
        if item.deadline is not None and (item.late_by_days or 0) > 0
    )
    rows = (
        SchedulingRecordViewModel(
            id="constraints",
            title="Deadline Breaches",
            status_label="Danger" if constraints else "Stable",
            subtitle=str(constraints),
            supporting_text="Activities missing their current deadline guard.",
            meta_text="Deadline control",
        ),
    )
    return SchedulingCollectionViewModel(
        title="Diagnostics",
        subtitle="Planner checks for network quality, float pressure, and resource overload.",
        items=rows,
        empty_state="No diagnostics are available yet.",
    )

__all__ = ["build_diagnostics_collection"]
