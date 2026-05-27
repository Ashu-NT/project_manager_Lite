from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MaintenanceWorkRequestOptionViewModel:
    value: str
    label: str


@dataclass(frozen=True)
class MaintenanceWorkRequestMetricViewModel:
    label: str
    value: str
    supporting_text: str


@dataclass(frozen=True)
class MaintenanceWorkRequestOverviewViewModel:
    title: str
    subtitle: str
    metrics: tuple[MaintenanceWorkRequestMetricViewModel, ...] = field(
        default_factory=tuple
    )


@dataclass(frozen=True)
class MaintenanceWorkRequestRecordViewModel:
    id: str
    title: str
    status_label: str
    subtitle: str
    supporting_text: str
    meta_text: str
    state: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class MaintenanceWorkRequestDetailFieldViewModel:
    label: str
    value: str
    supporting_text: str = ""


@dataclass(frozen=True)
class MaintenanceWorkRequestDetailViewModel:
    id: str = ""
    title: str = ""
    status_label: str = ""
    subtitle: str = ""
    description: str = ""
    empty_state: str = ""
    fields: tuple[MaintenanceWorkRequestDetailFieldViewModel, ...] = field(
        default_factory=tuple
    )
    state: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class MaintenanceWorkRequestsWorkspaceViewModel:
    overview: MaintenanceWorkRequestOverviewViewModel
    site_options: tuple[MaintenanceWorkRequestOptionViewModel, ...] = field(
        default_factory=tuple
    )
    status_options: tuple[MaintenanceWorkRequestOptionViewModel, ...] = field(
        default_factory=tuple
    )
    priority_options: tuple[MaintenanceWorkRequestOptionViewModel, ...] = field(
        default_factory=tuple
    )
    asset_options: tuple[MaintenanceWorkRequestOptionViewModel, ...] = field(
        default_factory=tuple
    )
    selected_site_filter: str = "all"
    selected_status_filter: str = "all"
    selected_priority_filter: str = "all"
    selected_asset_filter: str = "all"
    search_text: str = ""
    work_requests: tuple[MaintenanceWorkRequestRecordViewModel, ...] = field(
        default_factory=tuple
    )
    selected_work_request_id: str = ""
    selected_work_request_detail: MaintenanceWorkRequestDetailViewModel = field(
        default_factory=MaintenanceWorkRequestDetailViewModel
    )
    form_site_options: tuple[MaintenanceWorkRequestOptionViewModel, ...] = field(
        default_factory=tuple
    )
    form_location_options: tuple[MaintenanceWorkRequestOptionViewModel, ...] = field(
        default_factory=tuple
    )
    form_system_options: tuple[MaintenanceWorkRequestOptionViewModel, ...] = field(
        default_factory=tuple
    )
    form_asset_options: tuple[MaintenanceWorkRequestOptionViewModel, ...] = field(
        default_factory=tuple
    )
    form_component_options: tuple[MaintenanceWorkRequestOptionViewModel, ...] = field(
        default_factory=tuple
    )
    form_source_type_options: tuple[MaintenanceWorkRequestOptionViewModel, ...] = field(
        default_factory=tuple
    )
    form_priority_options: tuple[MaintenanceWorkRequestOptionViewModel, ...] = field(
        default_factory=tuple
    )
    form_status_options: tuple[MaintenanceWorkRequestOptionViewModel, ...] = field(
        default_factory=tuple
    )
    empty_state: str = ""


__all__ = [
    "MaintenanceWorkRequestDetailFieldViewModel",
    "MaintenanceWorkRequestDetailViewModel",
    "MaintenanceWorkRequestMetricViewModel",
    "MaintenanceWorkRequestOptionViewModel",
    "MaintenanceWorkRequestOverviewViewModel",
    "MaintenanceWorkRequestRecordViewModel",
    "MaintenanceWorkRequestsWorkspaceViewModel",
]
