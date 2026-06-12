from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.reliability import (
    MaintenanceReliabilityMetricViewModel,
    MaintenanceReliabilityOverviewViewModel,
)


def map_overview(snapshot_overview) -> MaintenanceReliabilityOverviewViewModel:
    return MaintenanceReliabilityOverviewViewModel(
        title=snapshot_overview.title,
        subtitle=snapshot_overview.subtitle,
        metrics=tuple(
            MaintenanceReliabilityMetricViewModel(
                label=metric.label,
                value=metric.value,
                supporting_text=metric.supporting_text,
            )
            for metric in snapshot_overview.metrics
        ),
    )
