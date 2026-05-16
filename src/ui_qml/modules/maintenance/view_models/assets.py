from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MaintenanceAssetLibraryOptionViewModel:
    value: str
    label: str


@dataclass(frozen=True)
class MaintenanceAssetLibraryMetricViewModel:
    label: str
    value: str
    supporting_text: str


@dataclass(frozen=True)
class MaintenanceAssetLibraryOverviewViewModel:
    title: str
    subtitle: str
    metrics: tuple[MaintenanceAssetLibraryMetricViewModel, ...] = field(
        default_factory=tuple
    )


@dataclass(frozen=True)
class MaintenanceAssetLibraryRecordViewModel:
    id: str
    title: str
    status_label: str
    subtitle: str
    supporting_text: str
    meta_text: str
    state: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class MaintenanceAssetLibraryCatalogViewModel:
    title: str
    subtitle: str
    empty_state: str = ""
    items: tuple[MaintenanceAssetLibraryRecordViewModel, ...] = field(
        default_factory=tuple
    )


@dataclass(frozen=True)
class MaintenanceAssetLibraryDetailFieldViewModel:
    label: str
    value: str
    supporting_text: str = ""


@dataclass(frozen=True)
class MaintenanceAssetLibraryDetailViewModel:
    id: str = ""
    title: str = ""
    status_label: str = ""
    subtitle: str = ""
    description: str = ""
    empty_state: str = ""
    fields: tuple[MaintenanceAssetLibraryDetailFieldViewModel, ...] = field(
        default_factory=tuple
    )
    state: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class MaintenanceAssetsWorkspaceViewModel:
    overview: MaintenanceAssetLibraryOverviewViewModel
    site_options: tuple[MaintenanceAssetLibraryOptionViewModel, ...] = field(
        default_factory=tuple
    )
    active_filter_options: tuple[MaintenanceAssetLibraryOptionViewModel, ...] = field(
        default_factory=tuple
    )
    selected_site_filter: str = "all"
    selected_active_filter: str = "all"
    search_text: str = ""
    locations: MaintenanceAssetLibraryCatalogViewModel = field(
        default_factory=lambda: MaintenanceAssetLibraryCatalogViewModel(
            title="Locations",
            subtitle="",
        )
    )
    systems: MaintenanceAssetLibraryCatalogViewModel = field(
        default_factory=lambda: MaintenanceAssetLibraryCatalogViewModel(
            title="Systems",
            subtitle="",
        )
    )
    assets: MaintenanceAssetLibraryCatalogViewModel = field(
        default_factory=lambda: MaintenanceAssetLibraryCatalogViewModel(
            title="Assets",
            subtitle="",
        )
    )
    components: MaintenanceAssetLibraryCatalogViewModel = field(
        default_factory=lambda: MaintenanceAssetLibraryCatalogViewModel(
            title="Components",
            subtitle="",
        )
    )
    selected_location_id: str = ""
    selected_system_id: str = ""
    selected_asset_id: str = ""
    selected_component_id: str = ""
    selected_location_detail: MaintenanceAssetLibraryDetailViewModel = field(
        default_factory=MaintenanceAssetLibraryDetailViewModel
    )
    selected_system_detail: MaintenanceAssetLibraryDetailViewModel = field(
        default_factory=MaintenanceAssetLibraryDetailViewModel
    )
    selected_asset_detail: MaintenanceAssetLibraryDetailViewModel = field(
        default_factory=MaintenanceAssetLibraryDetailViewModel
    )
    selected_component_detail: MaintenanceAssetLibraryDetailViewModel = field(
        default_factory=MaintenanceAssetLibraryDetailViewModel
    )
    form_site_options: tuple[MaintenanceAssetLibraryOptionViewModel, ...] = field(
        default_factory=tuple
    )
    form_location_options: tuple[MaintenanceAssetLibraryOptionViewModel, ...] = field(
        default_factory=tuple
    )
    form_parent_location_options: tuple[
        MaintenanceAssetLibraryOptionViewModel, ...
    ] = field(default_factory=tuple)
    form_system_options: tuple[MaintenanceAssetLibraryOptionViewModel, ...] = field(
        default_factory=tuple
    )
    form_parent_system_options: tuple[
        MaintenanceAssetLibraryOptionViewModel, ...
    ] = field(default_factory=tuple)
    form_asset_options: tuple[MaintenanceAssetLibraryOptionViewModel, ...] = field(
        default_factory=tuple
    )
    form_parent_asset_options: tuple[
        MaintenanceAssetLibraryOptionViewModel, ...
    ] = field(default_factory=tuple)
    form_component_options: tuple[
        MaintenanceAssetLibraryOptionViewModel, ...
    ] = field(default_factory=tuple)
    form_parent_component_options: tuple[
        MaintenanceAssetLibraryOptionViewModel, ...
    ] = field(default_factory=tuple)
    form_status_options: tuple[MaintenanceAssetLibraryOptionViewModel, ...] = field(
        default_factory=tuple
    )
    form_criticality_options: tuple[
        MaintenanceAssetLibraryOptionViewModel, ...
    ] = field(default_factory=tuple)
    form_manufacturer_options: tuple[
        MaintenanceAssetLibraryOptionViewModel, ...
    ] = field(default_factory=tuple)
    form_supplier_options: tuple[MaintenanceAssetLibraryOptionViewModel, ...] = field(
        default_factory=tuple
    )
    empty_state: str = ""


__all__ = [
    "MaintenanceAssetLibraryCatalogViewModel",
    "MaintenanceAssetLibraryDetailFieldViewModel",
    "MaintenanceAssetLibraryDetailViewModel",
    "MaintenanceAssetLibraryMetricViewModel",
    "MaintenanceAssetLibraryOptionViewModel",
    "MaintenanceAssetLibraryOverviewViewModel",
    "MaintenanceAssetLibraryRecordViewModel",
    "MaintenanceAssetsWorkspaceViewModel",
]
