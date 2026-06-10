from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.dashboard import (
    ProjectDashboardActivityFeedViewModel,
    ProjectDashboardChartViewModel,
    ProjectDashboardHealthCardViewModel,
    ProjectDashboardOperationalTableViewModel,
    ProjectDashboardOverviewViewModel,
    ProjectDashboardPanelViewModel,
    ProjectDashboardSectionViewModel,
)


def serialize_dashboard_overview_view_model(
    view_model: ProjectDashboardOverviewViewModel,
) -> dict[str, object]:
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "metrics": [
            {
                "label": metric.label,
                "value": metric.value,
                "supportingText": metric.supporting_text,
            }
            for metric in view_model.metrics
        ],
    }


def serialize_dashboard_section_view_models(view_models) -> list[dict[str, object]]:
    return [
        {
            "title": view_model.title,
            "subtitle": view_model.subtitle,
            "emptyState": view_model.empty_state,
            "items": [
                {
                    "id": item.id,
                    "title": item.title,
                    "statusLabel": item.status_label,
                    "subtitle": item.subtitle,
                    "supportingText": item.supporting_text,
                    "metaText": item.meta_text,
                    "state": dict(item.state),
                }
                for item in view_model.items
            ],
        }
        for view_model in view_models
    ]


def serialize_dashboard_health_card_view_models(
    view_models: tuple[ProjectDashboardHealthCardViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "id": view_model.id,
            "title": view_model.title,
            "statusLabel": view_model.status_label,
            "metricValue": view_model.metric_value,
            "metricLabel": view_model.metric_label,
            "supportingText": view_model.supporting_text,
            "metaText": view_model.meta_text,
            "tone": view_model.tone,
            "routeId": view_model.route_id,
        }
        for view_model in view_models
    ]


def serialize_dashboard_operational_tab_view_models(view_models) -> list[dict[str, object]]:
    return [
        {
            "id": view_model.id,
            "label": view_model.label,
            "count": view_model.count,
            "routeId": view_model.route_id,
        }
        for view_model in view_models
    ]


def serialize_dashboard_operational_table_view_models(
    view_models: tuple[ProjectDashboardOperationalTableViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "id": view_model.id,
            "title": view_model.title,
            "subtitle": view_model.subtitle,
            "emptyState": view_model.empty_state,
            "columns": [
                {
                    "key": column.key,
                    "label": column.label,
                    "flex": column.flex,
                    "minWidth": column.min_width,
                    "sortable": column.sortable,
                    "visible": column.visible,
                    "type": column.column_type,
                }
                for column in view_model.columns
            ],
            "rows": [
                {
                    "id": row.id,
                    **dict(row.values),
                    "routeId": row.route_id,
                    "state": dict(row.state),
                }
                for row in view_model.rows
            ],
        }
        for view_model in view_models
    ]


def serialize_dashboard_activity_feed_view_model(
    view_model: ProjectDashboardActivityFeedViewModel | None,
) -> dict[str, object]:
    if view_model is None:
        return {
            "title": "Recent Activity",
            "subtitle": "",
            "emptyState": "No recent activity is available yet.",
            "items": [],
        }
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "emptyState": view_model.empty_state,
        "items": [
            {
                "id": item.id,
                "title": item.title,
                "statusLabel": item.status_label,
                "metaText": item.meta_text,
                "routeId": item.route_id,
                "state": dict(item.state),
            }
            for item in view_model.items
        ],
    }


def serialize_dashboard_panel_view_models(
    view_models: tuple[ProjectDashboardPanelViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "title": view_model.title,
            "subtitle": view_model.subtitle,
            "hint": view_model.hint,
            "emptyState": view_model.empty_state,
            "rows": [
                {
                    "label": row.label,
                    "value": row.value,
                    "supportingText": row.supporting_text,
                    "tone": row.tone,
                }
                for row in view_model.rows
            ],
            "metrics": [
                {
                    "label": metric.label,
                    "value": metric.value,
                    "supportingText": metric.supporting_text,
                }
                for metric in view_model.metrics
            ],
        }
        for view_model in view_models
    ]


def serialize_dashboard_chart_view_models(
    view_models: tuple[ProjectDashboardChartViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "title": view_model.title,
            "subtitle": view_model.subtitle,
            "chartType": view_model.chart_type,
            "emptyState": view_model.empty_state,
            "points": [
                {
                    "label": point.label,
                    "value": point.value,
                    "valueLabel": point.value_label,
                    "supportingText": point.supporting_text,
                    "targetValue": point.target_value,
                    "tone": point.tone,
                }
                for point in view_model.points
            ],
        }
        for view_model in view_models
    ]


__all__ = [
    "serialize_dashboard_activity_feed_view_model",
    "serialize_dashboard_chart_view_models",
    "serialize_dashboard_health_card_view_models",
    "serialize_dashboard_operational_tab_view_models",
    "serialize_dashboard_operational_table_view_models",
    "serialize_dashboard_overview_view_model",
    "serialize_dashboard_panel_view_models",
    "serialize_dashboard_section_view_models",
]
