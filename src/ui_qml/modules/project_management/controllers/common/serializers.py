from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.dashboard import (
    ProjectDashboardChartViewModel,
    ProjectDashboardOverviewViewModel,
    ProjectDashboardPanelViewModel,
)
from src.ui_qml.modules.project_management.view_models.workspace import (
    ProjectManagementWorkspaceViewModel,
)


def serialize_workspace_view_model(
    view_model: ProjectManagementWorkspaceViewModel,
) -> dict[str, str]:
    return {
        "routeId": view_model.route_id,
        "title": view_model.title,
        "summary": view_model.summary,
        "migrationStatus": view_model.migration_status,
        "legacyRuntimeStatus": view_model.legacy_runtime_status,
    }


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


def serialize_selector_options(view_models) -> list[dict[str, str]]:
    return [
        {
            "value": view_model.value,
            "label": view_model.label,
        }
        for view_model in view_models
    ]


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
    "serialize_dashboard_chart_view_models",
    "serialize_dashboard_overview_view_model",
    "serialize_dashboard_panel_view_models",
    "serialize_dashboard_section_view_models",
    "serialize_selector_options",
    "serialize_workspace_view_model",
]
