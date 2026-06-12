from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.dashboard import (
    MaintenanceDashboardOverviewViewModel,
    MaintenanceMetricViewModel,
)


def map_overview(overview) -> MaintenanceDashboardOverviewViewModel:
    return MaintenanceDashboardOverviewViewModel(
        title=overview.title,
        subtitle=overview.subtitle,
        metrics=tuple(
            MaintenanceMetricViewModel(
                label=metric.label,
                value=metric.value,
                supporting_text=metric.supporting_text,
            )
            for metric in overview.metrics
        ),
    )
