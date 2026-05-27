from __future__ import annotations

from dataclasses import dataclass, field

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryCatalogMetricViewModel,
    InventoryRecordViewModel,
    InventorySelectorOptionViewModel,
)


@dataclass(frozen=True)
class InventoryModuleLinkViewModel:
    code: str
    label: str
    kind: str
    is_enabled: bool
    status_label: str
    reason: str
    route_id: str


@dataclass(frozen=True)
class InventoryInventoryFoundationViewModel:
    title: str
    subtitle: str
    metrics: tuple[InventoryCatalogMetricViewModel, ...] = field(default_factory=tuple)
    module_links: tuple[InventoryModuleLinkViewModel, ...] = field(default_factory=tuple)
    location_type_options: tuple[InventorySelectorOptionViewModel, ...] = field(default_factory=tuple)
    cycle_count_status_options: tuple[InventorySelectorOptionViewModel, ...] = field(default_factory=tuple)
    locations: tuple[InventoryRecordViewModel, ...] = field(default_factory=tuple)
    reorder_policies: tuple[InventoryRecordViewModel, ...] = field(default_factory=tuple)
    cycle_counts: tuple[InventoryRecordViewModel, ...] = field(default_factory=tuple)
    valuation_signals: tuple[InventoryRecordViewModel, ...] = field(default_factory=tuple)
    tracking_signals: tuple[InventoryRecordViewModel, ...] = field(default_factory=tuple)
    activity_signals: tuple[InventoryRecordViewModel, ...] = field(default_factory=tuple)


__all__ = [
    "InventoryInventoryFoundationViewModel",
    "InventoryModuleLinkViewModel",
]
