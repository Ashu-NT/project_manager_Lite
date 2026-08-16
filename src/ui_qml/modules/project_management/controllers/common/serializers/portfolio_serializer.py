from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.portfolio import (
    PortfolioCollectionViewModel,
    PortfolioOverviewViewModel,
    PortfolioPagedCollectionViewModel,
    PortfolioRecordViewModel,
    PortfolioSummaryViewModel,
)


def serialize_portfolio_overview_view_model(
    view_model: PortfolioOverviewViewModel,
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


def serialize_portfolio_record_view_models(
    view_models: tuple[PortfolioRecordViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "id": view_model.id,
            "title": view_model.title,
            "statusLabel": view_model.status_label,
            "subtitle": view_model.subtitle,
            "supportingText": view_model.supporting_text,
            "metaText": view_model.meta_text,
            "canPrimaryAction": view_model.can_primary_action,
            "canSecondaryAction": view_model.can_secondary_action,
            "canTertiaryAction": view_model.can_tertiary_action,
            "state": dict(view_model.state),
        }
        for view_model in view_models
    ]


def serialize_portfolio_collection_view_model(
    view_model: PortfolioCollectionViewModel,
) -> dict[str, object]:
    payload = {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "emptyState": view_model.empty_state,
        "items": serialize_portfolio_record_view_models(view_model.items),
    }
    if isinstance(view_model, PortfolioPagedCollectionViewModel):
        payload.update(
            {
                "total": view_model.total,
                "page": view_model.page,
                "pageSize": view_model.page_size,
                "sortKey": view_model.sort_key,
                "sortDirection": view_model.sort_direction,
                "searchText": view_model.search_text,
            }
        )
    return payload


def serialize_portfolio_summary_view_model(
    view_model: PortfolioSummaryViewModel,
) -> dict[str, object]:
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "emptyState": view_model.empty_state,
        "fields": [
            {
                "label": field.label,
                "value": field.value,
                "supportingText": field.supporting_text,
            }
            for field in view_model.fields
        ],
    }


__all__ = [
    "serialize_portfolio_collection_view_model",
    "serialize_portfolio_overview_view_model",
    "serialize_portfolio_record_view_models",
    "serialize_portfolio_summary_view_model",
]
