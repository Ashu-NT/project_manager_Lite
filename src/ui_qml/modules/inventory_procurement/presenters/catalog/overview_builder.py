from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryCatalogMetricViewModel,
    InventoryCatalogOverviewViewModel,
)


def build_overview(
    *,
    all_categories,
    all_items,
    filtered_categories,
    filtered_items,
) -> InventoryCatalogOverviewViewModel:
    equipment_count = sum(1 for category in all_categories if category.is_equipment)
    project_usage_count = sum(
        1 for category in all_categories if category.supports_project_usage
    )
    maintenance_usage_count = sum(
        1 for category in all_categories if category.supports_maintenance_usage
    )
    active_item_count = sum(1 for item in all_items if item.is_active)
    stocked_item_count = sum(1 for item in all_items if item.is_stocked)
    purchasable_item_count = sum(1 for item in all_items if item.is_purchase_allowed)
    return InventoryCatalogOverviewViewModel(
        title="Catalog",
        subtitle="Category governance, reusable inventory items, supplier context, and linked document workflows.",
        metrics=(
            InventoryCatalogMetricViewModel(
                label="Categories",
                value=str(len(all_categories)),
                supporting_text=f"Showing {len(filtered_categories)} category records with the current filters.",
            ),
            InventoryCatalogMetricViewModel(
                label="Equipment",
                value=str(equipment_count),
                supporting_text="Categories flagged for reusable equipment and fleet-style assets.",
            ),
            InventoryCatalogMetricViewModel(
                label="Project usage",
                value=str(project_usage_count),
                supporting_text="Categories available to project-side planning and execution.",
            ),
            InventoryCatalogMetricViewModel(
                label="Maintenance usage",
                value=str(maintenance_usage_count),
                supporting_text="Categories available to maintenance spare and work-order flows.",
            ),
            InventoryCatalogMetricViewModel(
                label="Active items",
                value=str(active_item_count),
                supporting_text=f"{stocked_item_count} stocked, {purchasable_item_count} purchasable.",
            ),
            InventoryCatalogMetricViewModel(
                label="Filtered items",
                value=str(len(filtered_items)),
                supporting_text="Item rows that match the current catalog filters.",
            ),
        ),
    )
