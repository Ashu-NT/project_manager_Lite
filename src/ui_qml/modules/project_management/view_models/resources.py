from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ResourceCatalogMetricViewModel:
    label: str
    value: str
    supporting_text: str


@dataclass(frozen=True)
class ResourceCatalogOverviewViewModel:
    title: str
    subtitle: str
    metrics: tuple[ResourceCatalogMetricViewModel, ...]


@dataclass(frozen=True)
class ResourceSelectorOptionViewModel:
    value: str
    label: str


@dataclass(frozen=True)
class ResourceEmployeeOptionViewModel:
    value: str
    label: str
    name: str
    title: str
    contact: str
    context: str
    is_active: bool


@dataclass(frozen=True)
class ResourceRecordViewModel:
    id: str
    title: str
    status_label: str
    subtitle: str
    supporting_text: str
    meta_text: str
    can_primary_action: bool = True
    can_secondary_action: bool = True
    can_tertiary_action: bool = True
    state: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ResourceDetailFieldViewModel:
    label: str
    value: str
    supporting_text: str = ""


@dataclass(frozen=True)
class ResourceDetailViewModel:
    id: str = ""
    title: str = ""
    status_label: str = ""
    subtitle: str = ""
    description: str = ""
    empty_state: str = ""
    fields: tuple[ResourceDetailFieldViewModel, ...] = field(default_factory=tuple)
    state: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ResourceCatalogWorkspaceViewModel:
    overview: ResourceCatalogOverviewViewModel
    worker_type_options: tuple[ResourceSelectorOptionViewModel, ...] = field(default_factory=tuple)
    category_options: tuple[ResourceSelectorOptionViewModel, ...] = field(default_factory=tuple)
    employee_options: tuple[ResourceEmployeeOptionViewModel, ...] = field(default_factory=tuple)
    selected_active_filter: str = "all"
    selected_category_filter: str = "all"
    search_text: str = ""
    resources: tuple[ResourceRecordViewModel, ...] = field(default_factory=tuple)
    selected_resource_id: str = ""
    selected_resource_detail: ResourceDetailViewModel = field(default_factory=ResourceDetailViewModel)
    empty_state: str = ""


__all__ = [
    "ResourceCatalogMetricViewModel",
    "ResourceCatalogOverviewViewModel",
    "ResourceCatalogWorkspaceViewModel",
    "ResourceDetailFieldViewModel",
    "ResourceDetailViewModel",
    "ResourceEmployeeOptionViewModel",
    "ResourceRecordViewModel",
    "ResourceSelectorOptionViewModel",
]
