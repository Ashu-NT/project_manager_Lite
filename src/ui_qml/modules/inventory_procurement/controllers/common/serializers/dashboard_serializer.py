from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.dashboard import (
    InventoryDashboardOverviewViewModel,
    InventoryDashboardSectionViewModel,
)


def serialize_dashboard_overview_view_model(
    view_model: InventoryDashboardOverviewViewModel,
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


def serialize_dashboard_section_view_models(
    view_models: tuple[InventoryDashboardSectionViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "title": view_model.title,
            "subtitle": view_model.subtitle,
            "emptyState": view_model.empty_state,
            "rows": [
                {
                    "id": row.id,
                    "title": row.title,
                    "subtitle": row.subtitle,
                    "statusLabel": row.status_label,
                    "supportingText": row.supporting_text,
                    "metaText": row.meta_text,
                    "tone": row.tone,
                }
                for row in view_model.rows
            ],
        }
        for view_model in view_models
    ]
