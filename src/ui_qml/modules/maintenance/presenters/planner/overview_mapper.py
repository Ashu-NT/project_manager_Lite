from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.planner import (
    MaintenancePlannerMetricViewModel,
    MaintenancePlannerOverviewViewModel,
)


def map_overview(snapshot_overview) -> MaintenancePlannerOverviewViewModel:
    return MaintenancePlannerOverviewViewModel(
        title=snapshot_overview.title,
        subtitle=snapshot_overview.subtitle,
        metrics=tuple(
            MaintenancePlannerMetricViewModel(
                label=metric.label,
                value=metric.value,
                supporting_text=metric.supporting_text,
            )
            for metric in snapshot_overview.metrics
        ),
    )
