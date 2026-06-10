from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.dashboard import (
    ProjectDashboardMetricViewModel,
    ProjectDashboardOverviewViewModel,
)


def to_overview_view_model(descriptor) -> ProjectDashboardOverviewViewModel:
    return ProjectDashboardOverviewViewModel(
        title=descriptor.title,
        subtitle=descriptor.subtitle,
        metrics=tuple(
            ProjectDashboardMetricViewModel(
                label=metric.label,
                value=metric.value,
                supporting_text=metric.supporting_text,
            )
            for metric in descriptor.metrics
        ),
    )
