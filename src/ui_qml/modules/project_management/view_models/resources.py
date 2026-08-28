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
    department: str
    site: str
    department_id: str
    site_id: str
    is_active: bool

@dataclass(frozen=True)
class ResourceScopeOptionViewModel:
    value: str
    label: str
    is_active: bool
    site_id: str = ""

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
class ResourceInspectorViewModel:
    id: str = ""
    title: str = ""
    status_label: str = ""
    fields: tuple[ResourceDetailFieldViewModel, ...] = field(default_factory=tuple)
    state: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class ResourceAvailabilityDayViewModel:
    work_date: str
    date_label: str
    base_capacity_hours: float
    effective_capacity_hours: float
    planned_commitment_hours: float
    remaining_capacity_hours: float
    utilization_percent: float | None
    utilization_label: str
    overallocated: bool
    assignment_count: int

@dataclass(frozen=True)
class ResourceAvailabilityViewModel:
    resource_id: str = ""
    start_date: str = ""
    end_date: str = ""
    from_date_label: str = ""
    to_date_label: str = ""
    calendar_source_label: str = ""
    capacity_percent: float = 0.0
    base_capacity_hours: float = 0.0
    effective_capacity_hours: float = 0.0
    planned_commitment_hours: float = 0.0
    allocated_planned_hours: float = 0.0
    remaining_capacity_hours: float = 0.0
    utilization_percent: float | None = None
    utilization_label: str = "N/A"
    overallocated: bool = False
    conflict_days: int = 0
    project_count: int = 0
    assignment_count: int = 0
    days: tuple[ResourceAvailabilityDayViewModel, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class ResourceCatalogWorkspaceViewModel:
    overview: ResourceCatalogOverviewViewModel
    worker_type_options: tuple[ResourceSelectorOptionViewModel, ...] = field(default_factory=tuple)
    kind_options: tuple[ResourceSelectorOptionViewModel, ...] = field(default_factory=tuple)
    category_options: tuple[ResourceSelectorOptionViewModel, ...] = field(default_factory=tuple)
    department_options: tuple[ResourceScopeOptionViewModel, ...] = field(default_factory=tuple)
    site_options: tuple[ResourceScopeOptionViewModel, ...] = field(default_factory=tuple)
    employee_options: tuple[ResourceEmployeeOptionViewModel, ...] = field(default_factory=tuple)
    selected_active_filter: str = "all"
    selected_category_filter: str = "all"
    search_text: str = ""
    resources: tuple[ResourceRecordViewModel, ...] = field(default_factory=tuple)
    selected_resource_id: str = ""
    empty_state: str = ""
    total_count: int = 0
    page: int = 1
    page_size: int = 25
    sort_key: str = "catalog"
    sort_direction: str = "asc"

__all__ = [
    "ResourceAvailabilityDayViewModel",
    "ResourceAvailabilityViewModel",
    "ResourceCatalogMetricViewModel",
    "ResourceCatalogOverviewViewModel",
    "ResourceCatalogWorkspaceViewModel",
    "ResourceDetailFieldViewModel",
    "ResourceDetailViewModel",
    "ResourceEmployeeOptionViewModel",
    "ResourceInspectorViewModel",
    "ResourceRecordViewModel",
    "ResourceSelectorOptionViewModel",
    "ResourceScopeOptionViewModel",
]
