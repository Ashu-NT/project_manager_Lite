from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.assets import (
    MaintenanceAssetLibraryCatalogViewModel,
    MaintenanceAssetLibraryOptionViewModel,
    MaintenanceAssetsWorkspaceViewModel,
)

from .asset_detail_builder import build_asset_detail
from .asset_mapper import to_asset_record_view_model
from .component_detail_builder import build_component_detail
from .component_mapper import to_component_record_view_model
from .filtering import active_only_for_filter, matches_search, normalize_filter
from .location_detail_builder import build_location_detail
from .location_mapper import to_location_record_view_model
from .overview_builder import build_overview
from .selection import resolve_selected_id
from .system_detail_builder import build_system_detail
from .system_mapper import to_system_record_view_model


def _option(value: str, label: str) -> MaintenanceAssetLibraryOptionViewModel:
    return MaintenanceAssetLibraryOptionViewModel(value=value, label=label)


_ACTIVE_FILTER_OPTIONS = (
    _option("all", "All records"),
    _option("active", "Active only"),
    _option("inactive", "Inactive only"),
)


def _location_subtitle(*, selected_site: str) -> str:
    if selected_site != "all":
        return "Filtered to the selected site and activity status."
    return "Review site locations and location hierarchy records."


def _systems_subtitle(*, selected_location) -> str:
    if selected_location is not None:
        return f"Scoped to location: {selected_location.location_code} - {selected_location.name}"
    return "Review systems across the current site and activity filters."


def _assets_subtitle(*, selected_location, selected_system) -> str:
    if selected_system is not None:
        return f"Scoped to system: {selected_system.system_code} - {selected_system.name}"
    if selected_location is not None:
        return f"Scoped to location: {selected_location.location_code} - {selected_location.name}"
    return "Review asset records across the current site and activity filters."


def _components_subtitle(*, selected_asset) -> str:
    if selected_asset is not None:
        return f"Scoped to asset: {selected_asset.asset_code} - {selected_asset.name}"
    return "Review component records across the current activity filter."


def _build_catalog_empty_state(
    entity_label: str,
    *,
    rows,
    search_text: str,
    site_filter: str,
    active_filter: str,
    scope_label: str = "",
) -> str:
    if rows:
        return ""
    if search_text or site_filter != "all" or active_filter != "all" or scope_label:
        if scope_label:
            return f"No {entity_label} match the current filters and selected scope."
        return f"No {entity_label} match the current filters."
    return f"No {entity_label} are available yet."


def _build_workspace_empty_state(
    *,
    location_rows,
    system_rows,
    asset_rows,
    component_rows,
    search_text: str,
    site_filter: str,
    active_filter: str,
) -> str:
    if location_rows or system_rows or asset_rows or component_rows:
        return ""
    if search_text or site_filter != "all" or active_filter != "all":
        return "No maintenance asset-library records match the current filters."
    return "No maintenance asset-library records are available yet."


def build_workspace_state(
    desktop_api,
    *,
    search_text: str = "",
    site_filter: str = "all",
    active_filter: str = "all",
    selected_location_id: str | None = None,
    selected_system_id: str | None = None,
    selected_asset_id: str | None = None,
    selected_component_id: str | None = None,
) -> MaintenanceAssetsWorkspaceViewModel:
    site_options = (
        _option("all", "All sites"),
        *(
            _option(option.value, option.label)
            for option in desktop_api.list_sites(active_only=None)
        ),
    )
    normalized_site_filter = normalize_filter(site_filter, site_options)
    normalized_active_filter = normalize_filter(active_filter, _ACTIVE_FILTER_OPTIONS)
    active_only = active_only_for_filter(normalized_active_filter)
    normalized_search = (search_text or "").strip()

    site_id = None if normalized_site_filter == "all" else normalized_site_filter
    location_rows = tuple(
        row
        for row in desktop_api.list_locations(active_only=active_only, site_id=site_id)
        if matches_search(
            normalized_search,
            row.location_code,
            row.name,
            row.description,
            row.site_label,
            row.parent_location_label,
            row.location_type,
            row.criticality,
            row.criticality_label,
            row.status,
            row.status_label,
            row.notes,
        )
    )
    resolved_location_id = resolve_selected_id(selected_location_id, location_rows)
    scoped_location_id = resolved_location_id or None

    system_rows = tuple(
        row
        for row in desktop_api.list_systems(
            active_only=active_only,
            site_id=site_id,
            location_id=scoped_location_id,
        )
        if matches_search(
            normalized_search,
            row.system_code,
            row.name,
            row.description,
            row.site_label,
            row.location_label,
            row.parent_system_label,
            row.system_type,
            row.criticality,
            row.criticality_label,
            row.status,
            row.status_label,
            row.notes,
        )
    )
    resolved_system_id = resolve_selected_id(selected_system_id, system_rows)
    scoped_system_id = resolved_system_id or None

    asset_rows = tuple(
        row
        for row in desktop_api.list_assets(
            active_only=active_only,
            site_id=site_id,
            location_id=scoped_location_id,
            system_id=scoped_system_id,
        )
        if matches_search(
            normalized_search,
            row.asset_code,
            row.name,
            row.description,
            row.site_label,
            row.location_label,
            row.system_label,
            row.parent_asset_label,
            row.asset_type,
            row.asset_category,
            row.criticality,
            row.criticality_label,
            row.status,
            row.status_label,
            row.manufacturer_party_label,
            row.supplier_party_label,
            row.model_number,
            row.serial_number,
            row.barcode,
            row.maintenance_strategy,
            row.service_level,
            row.notes,
        )
    )
    resolved_asset_id = resolve_selected_id(selected_asset_id, asset_rows)
    scoped_asset_id = resolved_asset_id or None

    component_rows = tuple(
        row
        for row in desktop_api.list_components(
            active_only=active_only,
            asset_id=scoped_asset_id,
        )
        if matches_search(
            normalized_search,
            row.component_code,
            row.name,
            row.description,
            row.asset_label,
            row.parent_component_label,
            row.component_type,
            row.status,
            row.status_label,
            row.manufacturer_party_label,
            row.supplier_party_label,
            row.manufacturer_part_number,
            row.supplier_part_number,
            row.model_number,
            row.serial_number,
            row.notes,
        )
    )
    resolved_component_id = resolve_selected_id(selected_component_id, component_rows)

    selected_location = next(
        (row for row in location_rows if row.id == resolved_location_id),
        None,
    )
    selected_system = next(
        (row for row in system_rows if row.id == resolved_system_id),
        None,
    )
    selected_asset = next(
        (row for row in asset_rows if row.id == resolved_asset_id),
        None,
    )
    selected_component = next(
        (row for row in component_rows if row.id == resolved_component_id),
        None,
    )

    form_site_options = tuple(
        _option(option.value, option.label)
        for option in desktop_api.list_sites(active_only=None)
    )
    form_location_options = tuple(
        _option(option.value, option.label)
        for option in desktop_api.list_location_options(active_only=None, site_id=site_id)
    )
    form_system_options = tuple(
        _option(option.value, option.label)
        for option in desktop_api.list_system_options(active_only=None, site_id=site_id)
    )
    form_asset_options = tuple(
        _option(option.value, option.label)
        for option in desktop_api.list_asset_options(active_only=None, site_id=site_id)
    )
    form_component_options = tuple(
        _option(option.value, option.label)
        for option in desktop_api.list_component_options(active_only=None)
    )
    form_status_options = tuple(
        _option(option.value, option.label)
        for option in desktop_api.list_lifecycle_statuses()
    )
    form_criticality_options = tuple(
        _option(option.value, option.label)
        for option in desktop_api.list_criticalities()
    )
    form_manufacturer_options = tuple(
        _option(option.value, option.label)
        for option in desktop_api.list_manufacturer_parties(active_only=None)
    )
    form_supplier_options = tuple(
        _option(option.value, option.label)
        for option in desktop_api.list_supplier_parties(active_only=None)
    )

    return MaintenanceAssetsWorkspaceViewModel(
        overview=build_overview(
            location_rows=location_rows,
            system_rows=system_rows,
            asset_rows=asset_rows,
            component_rows=component_rows,
            site_filter=normalized_site_filter,
            active_filter=normalized_active_filter,
        ),
        site_options=site_options,
        active_filter_options=_ACTIVE_FILTER_OPTIONS,
        selected_site_filter=normalized_site_filter,
        selected_active_filter=normalized_active_filter,
        search_text=normalized_search,
        locations=MaintenanceAssetLibraryCatalogViewModel(
            title="Locations",
            subtitle=_location_subtitle(selected_site=normalized_site_filter),
            empty_state=_build_catalog_empty_state(
                "locations",
                rows=location_rows,
                search_text=normalized_search,
                site_filter=normalized_site_filter,
                active_filter=normalized_active_filter,
            ),
            items=tuple(to_location_record_view_model(row) for row in location_rows),
        ),
        systems=MaintenanceAssetLibraryCatalogViewModel(
            title="Systems",
            subtitle=_systems_subtitle(selected_location=selected_location),
            empty_state=_build_catalog_empty_state(
                "systems",
                rows=system_rows,
                search_text=normalized_search,
                site_filter=normalized_site_filter,
                active_filter=normalized_active_filter,
                scope_label=selected_location.name if selected_location else "",
            ),
            items=tuple(to_system_record_view_model(row) for row in system_rows),
        ),
        assets=MaintenanceAssetLibraryCatalogViewModel(
            title="Assets",
            subtitle=_assets_subtitle(
                selected_location=selected_location,
                selected_system=selected_system,
            ),
            empty_state=_build_catalog_empty_state(
                "assets",
                rows=asset_rows,
                search_text=normalized_search,
                site_filter=normalized_site_filter,
                active_filter=normalized_active_filter,
                scope_label=selected_system.name if selected_system else "",
            ),
            items=tuple(to_asset_record_view_model(row) for row in asset_rows),
        ),
        components=MaintenanceAssetLibraryCatalogViewModel(
            title="Components",
            subtitle=_components_subtitle(selected_asset=selected_asset),
            empty_state=_build_catalog_empty_state(
                "components",
                rows=component_rows,
                search_text=normalized_search,
                site_filter=normalized_site_filter,
                active_filter=normalized_active_filter,
                scope_label=selected_asset.name if selected_asset else "",
            ),
            items=tuple(to_component_record_view_model(row) for row in component_rows),
        ),
        selected_location_id=resolved_location_id,
        selected_system_id=resolved_system_id,
        selected_asset_id=resolved_asset_id,
        selected_component_id=resolved_component_id,
        selected_location_detail=build_location_detail(selected_location),
        selected_system_detail=build_system_detail(selected_system),
        selected_asset_detail=build_asset_detail(selected_asset),
        selected_component_detail=build_component_detail(selected_component),
        form_site_options=form_site_options,
        form_location_options=form_location_options,
        form_parent_location_options=form_location_options,
        form_system_options=form_system_options,
        form_parent_system_options=form_system_options,
        form_asset_options=form_asset_options,
        form_parent_asset_options=form_asset_options,
        form_component_options=form_component_options,
        form_parent_component_options=form_component_options,
        form_status_options=form_status_options,
        form_criticality_options=form_criticality_options,
        form_manufacturer_options=form_manufacturer_options,
        form_supplier_options=form_supplier_options,
        empty_state=_build_workspace_empty_state(
            location_rows=location_rows,
            system_rows=system_rows,
            asset_rows=asset_rows,
            component_rows=component_rows,
            search_text=normalized_search,
            site_filter=normalized_site_filter,
            active_filter=normalized_active_filter,
        ),
    )
