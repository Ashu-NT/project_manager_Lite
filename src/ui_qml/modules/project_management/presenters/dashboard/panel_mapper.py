from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.dashboard import (
    ProjectDashboardMetricViewModel,
    ProjectDashboardPanelRowViewModel,
    ProjectDashboardPanelViewModel,
)


def to_panels(panels) -> tuple[ProjectDashboardPanelViewModel, ...]:
    return tuple(
        ProjectDashboardPanelViewModel(
            title=panel.title,
            subtitle=panel.subtitle,
            hint=panel.hint,
            empty_state=panel.empty_state,
            rows=tuple(
                ProjectDashboardPanelRowViewModel(
                    label=row.label,
                    value=row.value,
                    supporting_text=row.supporting_text,
                    tone=row.tone,
                )
                for row in panel.rows
            ),
            metrics=tuple(
                ProjectDashboardMetricViewModel(
                    label=metric.label,
                    value=metric.value,
                    supporting_text=metric.supporting_text,
                )
                for metric in panel.metrics
            ),
        )
        for panel in panels
    )
