from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.dashboard import (
    InventoryDashboardMetricViewModel,
    InventoryDashboardOverviewViewModel,
)


def build_overview(snapshot) -> InventoryDashboardOverviewViewModel:
    return InventoryDashboardOverviewViewModel(
        title=snapshot.title,
        subtitle=snapshot.subtitle,
        metrics=tuple(
            InventoryDashboardMetricViewModel(
                label=metric.label,
                value=metric.value,
                supporting_text=metric.supporting_text,
            )
            for metric in snapshot.metrics
        ),
    )
