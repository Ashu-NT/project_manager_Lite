from __future__ import annotations

import logging

from src.core.modules.project_management.api.desktop import (
    ProjectManagementDashboardDesktopApi,
    build_project_management_dashboard_desktop_api,
)
from src.ui_qml.modules.project_management.view_models.dashboard import (
    ProjectDashboardActivityFeedViewModel,
    ProjectDashboardActivityItemViewModel,
    ProjectDashboardChartPointViewModel,
    ProjectDashboardChartViewModel,
    ProjectDashboardHealthCardViewModel,
    ProjectDashboardMetricViewModel,
    ProjectDashboardOverviewViewModel,
    ProjectDashboardOperationalTableViewModel,
    ProjectDashboardOperationalTabViewModel,
    ProjectDashboardPanelRowViewModel,
    ProjectDashboardPanelViewModel,
    ProjectDashboardSectionItemViewModel,
    ProjectDashboardSectionViewModel,
    ProjectDashboardSelectorOptionViewModel,
    ProjectDashboardTableColumnViewModel,
    ProjectDashboardTableRowViewModel,
    ProjectDashboardWorkspaceViewModel,
)

logger = logging.getLogger(__name__)


class ProjectDashboardWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: ProjectManagementDashboardDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_project_management_dashboard_desktop_api()
        self._build_workspace_state_count = 0

    def build_workspace_state(
        self,
        *,
        project_id: str | None = None,
        baseline_id: str | None = None,
        period_key: str | None = None,
        view_key: str | None = None,
    ) -> ProjectDashboardWorkspaceViewModel:
        self._build_workspace_state_count += 1
        logger.debug(
            "PM dashboard presenter build_workspace_state #%s project=%r baseline=%r period=%r view=%r",
            self._build_workspace_state_count,
            project_id,
            baseline_id,
            period_key,
            view_key,
        )
        snapshot = self._desktop_api.build_snapshot(
            project_id=project_id,
            baseline_id=baseline_id,
            period_key=period_key,
            view_key=view_key,
        )
        return ProjectDashboardWorkspaceViewModel(
            overview=self._to_overview_view_model(snapshot.overview),
            project_options=tuple(
                ProjectDashboardSelectorOptionViewModel(
                    value=option.value,
                    label=option.label,
                )
                for option in snapshot.project_options
            ),
            selected_project_id=snapshot.selected_project_id,
            baseline_options=tuple(
                ProjectDashboardSelectorOptionViewModel(
                    value=option.value,
                    label=option.label,
                )
                for option in snapshot.baseline_options
            ),
            selected_baseline_id=snapshot.selected_baseline_id,
            period_options=tuple(
                ProjectDashboardSelectorOptionViewModel(
                    value=option.value,
                    label=option.label,
                )
                for option in snapshot.period_options
            ),
            selected_period_key=snapshot.selected_period_key,
            view_options=tuple(
                ProjectDashboardSelectorOptionViewModel(
                    value=option.value,
                    label=option.label,
                )
                for option in snapshot.view_options
            ),
            selected_view_key=snapshot.selected_view_key,
            health_cards=tuple(
                ProjectDashboardHealthCardViewModel(
                    id=card.id,
                    title=card.title,
                    status_label=card.status_label,
                    metric_value=card.metric_value,
                    metric_label=card.metric_label,
                    supporting_text=card.supporting_text,
                    meta_text=card.meta_text,
                    tone=card.tone,
                    route_id=card.route_id,
                )
                for card in snapshot.health_cards
            ),
            operational_tabs=tuple(
                ProjectDashboardOperationalTabViewModel(
                    id=tab.id,
                    label=tab.label,
                    count=tab.count,
                    route_id=tab.route_id,
                )
                for tab in snapshot.operational_tabs
            ),
            operational_tables=tuple(
                ProjectDashboardOperationalTableViewModel(
                    id=table.id,
                    title=table.title,
                    subtitle=table.subtitle,
                    empty_state=table.empty_state,
                    columns=tuple(
                        ProjectDashboardTableColumnViewModel(
                            key=column.key,
                            label=column.label,
                            flex=column.flex,
                            min_width=column.min_width,
                            sortable=column.sortable,
                            visible=column.visible,
                            column_type=column.column_type,
                        )
                        for column in table.columns
                    ),
                    rows=tuple(
                        ProjectDashboardTableRowViewModel(
                            id=row.id,
                            values=dict(row.values),
                            route_id=row.route_id,
                            state=dict(row.state),
                        )
                        for row in table.rows
                    ),
                )
                for table in snapshot.operational_tables
            ),
            activity_feed=(
                ProjectDashboardActivityFeedViewModel(
                    title=snapshot.activity_feed.title,
                    subtitle=snapshot.activity_feed.subtitle,
                    empty_state=snapshot.activity_feed.empty_state,
                    items=tuple(
                        ProjectDashboardActivityItemViewModel(
                            id=item.id,
                            title=item.title,
                            status_label=item.status_label,
                            meta_text=item.meta_text,
                            route_id=item.route_id,
                            state=dict(item.state),
                        )
                        for item in snapshot.activity_feed.items
                    ),
                )
                if snapshot.activity_feed is not None
                else None
            ),
            panels=tuple(
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
                for panel in snapshot.panels
            ),
            charts=tuple(
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
                for chart in snapshot.charts
            ),
            sections=tuple(
                ProjectDashboardSectionViewModel(
                    title=section.title,
                    subtitle=section.subtitle,
                    empty_state=section.empty_state,
                    items=tuple(
                        ProjectDashboardSectionItemViewModel(
                            id=item.id,
                            title=item.title,
                            status_label=item.status_label,
                            subtitle=item.subtitle,
                            supporting_text=item.supporting_text,
                            meta_text=item.meta_text,
                            state=dict(item.state),
                        )
                        for item in section.items
                    ),
                )
                for section in snapshot.sections
            ),
            empty_state=snapshot.empty_state,
        )

    @staticmethod
    def _to_overview_view_model(descriptor) -> ProjectDashboardOverviewViewModel:
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


__all__ = ["ProjectDashboardWorkspacePresenter"]
