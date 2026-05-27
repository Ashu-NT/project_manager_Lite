from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MaintenanceWorkOrderOptionViewModel:
    value: str
    label: str


@dataclass(frozen=True)
class MaintenanceWorkOrderMetricViewModel:
    label: str
    value: str
    supporting_text: str


@dataclass(frozen=True)
class MaintenanceWorkOrderOverviewViewModel:
    title: str
    subtitle: str
    metrics: tuple[MaintenanceWorkOrderMetricViewModel, ...] = field(
        default_factory=tuple
    )


@dataclass(frozen=True)
class MaintenanceWorkOrderRecordViewModel:
    id: str
    title: str
    status_label: str
    subtitle: str
    supporting_text: str
    meta_text: str
    state: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class MaintenanceWorkOrderDetailFieldViewModel:
    label: str
    value: str
    supporting_text: str = ""


@dataclass(frozen=True)
class MaintenanceWorkOrderDetailViewModel:
    id: str = ""
    title: str = ""
    status_label: str = ""
    subtitle: str = ""
    description: str = ""
    empty_state: str = ""
    fields: tuple[MaintenanceWorkOrderDetailFieldViewModel, ...] = field(
        default_factory=tuple
    )
    state: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class MaintenanceWorkOrdersWorkspaceViewModel:
    overview: MaintenanceWorkOrderOverviewViewModel
    site_options: tuple[MaintenanceWorkOrderOptionViewModel, ...] = field(
        default_factory=tuple
    )
    status_options: tuple[MaintenanceWorkOrderOptionViewModel, ...] = field(
        default_factory=tuple
    )
    priority_options: tuple[MaintenanceWorkOrderOptionViewModel, ...] = field(
        default_factory=tuple
    )
    work_order_type_options: tuple[MaintenanceWorkOrderOptionViewModel, ...] = field(
        default_factory=tuple
    )
    asset_options: tuple[MaintenanceWorkOrderOptionViewModel, ...] = field(
        default_factory=tuple
    )
    selected_site_filter: str = "all"
    selected_status_filter: str = "all"
    selected_priority_filter: str = "all"
    selected_work_order_type_filter: str = "all"
    selected_asset_filter: str = "all"
    search_text: str = ""
    work_orders: tuple[MaintenanceWorkOrderRecordViewModel, ...] = field(
        default_factory=tuple
    )
    selected_work_order_id: str = ""
    selected_work_order_detail: MaintenanceWorkOrderDetailViewModel = field(
        default_factory=MaintenanceWorkOrderDetailViewModel
    )
    form_site_options: tuple[MaintenanceWorkOrderOptionViewModel, ...] = field(
        default_factory=tuple
    )
    form_location_options: tuple[MaintenanceWorkOrderOptionViewModel, ...] = field(
        default_factory=tuple
    )
    form_system_options: tuple[MaintenanceWorkOrderOptionViewModel, ...] = field(
        default_factory=tuple
    )
    form_asset_options: tuple[MaintenanceWorkOrderOptionViewModel, ...] = field(
        default_factory=tuple
    )
    form_component_options: tuple[MaintenanceWorkOrderOptionViewModel, ...] = field(
        default_factory=tuple
    )
    form_source_type_options: tuple[MaintenanceWorkOrderOptionViewModel, ...] = field(
        default_factory=tuple
    )
    form_source_work_request_options: tuple[
        MaintenanceWorkOrderOptionViewModel, ...
    ] = field(default_factory=tuple)
    form_work_order_type_options: tuple[
        MaintenanceWorkOrderOptionViewModel, ...
    ] = field(default_factory=tuple)
    form_priority_options: tuple[MaintenanceWorkOrderOptionViewModel, ...] = field(
        default_factory=tuple
    )
    form_status_options: tuple[MaintenanceWorkOrderOptionViewModel, ...] = field(
        default_factory=tuple
    )
    form_employee_options: tuple[MaintenanceWorkOrderOptionViewModel, ...] = field(
        default_factory=tuple
    )
    form_vendor_options: tuple[MaintenanceWorkOrderOptionViewModel, ...] = field(
        default_factory=tuple
    )
    empty_state: str = ""


__all__ = [
    "MaintenanceWorkOrderDetailFieldViewModel",
    "MaintenanceWorkOrderDetailViewModel",
    "MaintenanceWorkOrderMetricViewModel",
    "MaintenanceWorkOrderOptionViewModel",
    "MaintenanceWorkOrderOverviewViewModel",
    "MaintenanceWorkOrderRecordViewModel",
    "MaintenanceWorkOrdersWorkspaceViewModel",
]
