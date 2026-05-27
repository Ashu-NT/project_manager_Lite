from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class InventoryPricingMetricDescriptor:
    label: str
    value: str
    supporting_text: str


@dataclass(frozen=True)
class InventoryPricingRowDescriptor:
    id: str
    title: str
    subtitle: str = ""
    status_label: str = ""
    supporting_text: str = ""
    meta_text: str = ""
    tone: str = "default"


@dataclass(frozen=True)
class InventoryPricingSnapshotDescriptor:
    title: str
    subtitle: str
    context_label: str
    can_export: bool
    metrics: tuple[InventoryPricingMetricDescriptor, ...] = field(default_factory=tuple)
    stock_rows: tuple[InventoryPricingRowDescriptor, ...] = field(default_factory=tuple)
    supplier_price_rows: tuple[InventoryPricingRowDescriptor, ...] = field(default_factory=tuple)
    empty_state: str = ""


__all__ = [
    "InventoryPricingMetricDescriptor",
    "InventoryPricingRowDescriptor",
    "InventoryPricingSnapshotDescriptor",
]
