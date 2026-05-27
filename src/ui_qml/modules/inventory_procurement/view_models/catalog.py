from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class InventoryCatalogMetricViewModel:
    label: str
    value: str
    supporting_text: str


@dataclass(frozen=True)
class InventoryCatalogOverviewViewModel:
    title: str
    subtitle: str
    metrics: tuple[InventoryCatalogMetricViewModel, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class InventorySelectorOptionViewModel:
    value: str
    label: str


@dataclass(frozen=True)
class InventoryDocumentOptionViewModel:
    value: str
    label: str
    document_type: str
    storage_kind: str
    effective_date_label: str
    is_active: bool


@dataclass(frozen=True)
class InventoryRecordViewModel:
    id: str
    title: str
    status_label: str
    subtitle: str
    supporting_text: str
    meta_text: str
    can_primary_action: bool = True
    can_secondary_action: bool = True
    can_tertiary_action: bool = False
    state: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InventoryDetailFieldViewModel:
    label: str
    value: str
    supporting_text: str = ""


@dataclass(frozen=True)
class InventoryDetailViewModel:
    id: str = ""
    title: str = ""
    status_label: str = ""
    subtitle: str = ""
    description: str = ""
    empty_state: str = ""
    fields: tuple[InventoryDetailFieldViewModel, ...] = field(default_factory=tuple)
    linked_documents: tuple[InventoryDocumentOptionViewModel, ...] = field(default_factory=tuple)
    state: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InventoryCatalogWorkspaceViewModel:
    overview: InventoryCatalogOverviewViewModel
    active_options: tuple[InventorySelectorOptionViewModel, ...] = field(default_factory=tuple)
    usage_options: tuple[InventorySelectorOptionViewModel, ...] = field(default_factory=tuple)
    category_type_options: tuple[InventorySelectorOptionViewModel, ...] = field(default_factory=tuple)
    category_options: tuple[InventorySelectorOptionViewModel, ...] = field(default_factory=tuple)
    item_status_options: tuple[InventorySelectorOptionViewModel, ...] = field(default_factory=tuple)
    business_party_options: tuple[InventorySelectorOptionViewModel, ...] = field(default_factory=tuple)
    available_documents: tuple[InventoryDocumentOptionViewModel, ...] = field(default_factory=tuple)
    selected_active_filter: str = "all"
    selected_usage_filter: str = "all"
    selected_category_type_filter: str = "all"
    selected_category_filter: str = "all"
    search_text: str = ""
    categories: tuple[InventoryRecordViewModel, ...] = field(default_factory=tuple)
    selected_category_id: str = ""
    selected_category_detail: InventoryDetailViewModel = field(default_factory=InventoryDetailViewModel)
    items: tuple[InventoryRecordViewModel, ...] = field(default_factory=tuple)
    selected_item_id: str = ""
    selected_item_detail: InventoryDetailViewModel = field(default_factory=InventoryDetailViewModel)
    empty_state: str = ""


__all__ = [
    "InventoryCatalogMetricViewModel",
    "InventoryCatalogOverviewViewModel",
    "InventoryCatalogWorkspaceViewModel",
    "InventoryDetailFieldViewModel",
    "InventoryDetailViewModel",
    "InventoryDocumentOptionViewModel",
    "InventoryRecordViewModel",
    "InventorySelectorOptionViewModel",
]
