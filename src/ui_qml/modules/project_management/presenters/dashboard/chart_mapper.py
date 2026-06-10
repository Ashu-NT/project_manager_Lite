from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.dashboard import (
    ProjectDashboardChartPointViewModel,
    ProjectDashboardChartViewModel,
)


def to_charts(charts) -> tuple[ProjectDashboardChartViewModel, ...]:
    return tuple(
        ProjectDashboardChartViewModel(
            title=chart.title,
            subtitle=chart.subtitle,
            chart_type=chart.chart_type,
            empty_state=chart.empty_state,
            points=tuple(
                ProjectDashboardChartPointViewModel(
                    label=point.label,
                    value=point.value,
                    value_label=point.value_label,
                    supporting_text=point.supporting_text,
                    target_value=point.target_value,
                    tone=point.tone,
                )
                for point in chart.points
            ),
        )
        for chart in charts
    )
