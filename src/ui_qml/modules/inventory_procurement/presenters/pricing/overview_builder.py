from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryCatalogMetricViewModel,
    InventoryCatalogOverviewViewModel,
)


def build_overview(snapshot) -> InventoryCatalogOverviewViewModel:
    return InventoryCatalogOverviewViewModel(
        title=snapshot.title,
        subtitle=snapshot.subtitle,
        metrics=tuple(
            InventoryCatalogMetricViewModel(
                label=metric.label,
                value=metric.value,
                supporting_text=metric.supporting_text,
            )
            for metric in snapshot.metrics
        ),
    )
