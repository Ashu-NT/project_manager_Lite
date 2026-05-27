from __future__ import annotations

from typing import Any

from src.core.modules.maintenance.api.desktop import (
    MaintenanceAssetCreateCommand,
    MaintenanceAssetsDesktopApi,
    MaintenanceAssetUpdateCommand,
    MaintenanceComponentCreateCommand,
    MaintenanceComponentUpdateCommand,
    MaintenanceLocationCreateCommand,
    MaintenanceLocationUpdateCommand,
    MaintenanceSystemCreateCommand,
    MaintenanceSystemUpdateCommand,
    build_maintenance_assets_desktop_api,
)
from src.ui_qml.modules.maintenance.view_models.assets import (
    MaintenanceAssetLibraryCatalogViewModel,
    MaintenanceAssetLibraryDetailFieldViewModel,
    MaintenanceAssetLibraryDetailViewModel,
    MaintenanceAssetLibraryMetricViewModel,
    MaintenanceAssetLibraryOptionViewModel,
    MaintenanceAssetLibraryOverviewViewModel,
    MaintenanceAssetLibraryRecordViewModel,
    MaintenanceAssetsWorkspaceViewModel,
)


def _option(value: str, label: str) -> MaintenanceAssetLibraryOptionViewModel:
    return MaintenanceAssetLibraryOptionViewModel(value=value, label=label)


_ACTIVE_FILTER_OPTIONS = (
    _option("all", "All records"),
    _option("active", "Active only"),
    _option("inactive", "Inactive only"),
)


class MaintenanceAssetsWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: MaintenanceAssetsDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_maintenance_assets_desktop_api()

    def build_workspace_state(
        self,
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
                for option in self._desktop_api.list_sites(active_only=None)
            ),
        )
        normalized_site_filter = self._normalize_filter(site_filter, site_options)
        normalized_active_filter = self._normalize_filter(
            active_filter,
            _ACTIVE_FILTER_OPTIONS,
        )
        active_only = self._active_only_for_filter(normalized_active_filter)
        normalized_search = (search_text or "").strip()

        site_id = None if normalized_site_filter == "all" else normalized_site_filter
        location_rows = tuple(
            row
            for row in self._desktop_api.list_locations(
                active_only=active_only,
                site_id=site_id,
            )
            if self._matches_search(
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
        resolved_location_id = self._resolve_selected_id(
            selected_location_id,
            location_rows,
        )
        scoped_location_id = resolved_location_id or None

        system_rows = tuple(
            row
            for row in self._desktop_api.list_systems(
                active_only=active_only,
                site_id=site_id,
                location_id=scoped_location_id,
            )
            if self._matches_search(
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
        resolved_system_id = self._resolve_selected_id(
            selected_system_id,
            system_rows,
        )
        scoped_system_id = resolved_system_id or None

        asset_rows = tuple(
            row
            for row in self._desktop_api.list_assets(
                active_only=active_only,
                site_id=site_id,
                location_id=scoped_location_id,
                system_id=scoped_system_id,
            )
            if self._matches_search(
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
        resolved_asset_id = self._resolve_selected_id(
            selected_asset_id,
            asset_rows,
        )
        scoped_asset_id = resolved_asset_id or None

        component_rows = tuple(
            row
            for row in self._desktop_api.list_components(
                active_only=active_only,
                asset_id=scoped_asset_id,
            )
            if self._matches_search(
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
        resolved_component_id = self._resolve_selected_id(
            selected_component_id,
            component_rows,
        )

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
            for option in self._desktop_api.list_sites(active_only=None)
        )
        form_location_options = tuple(
            _option(option.value, option.label)
            for option in self._desktop_api.list_location_options(
                active_only=None,
                site_id=site_id,
            )
        )
        form_system_options = tuple(
            _option(option.value, option.label)
            for option in self._desktop_api.list_system_options(
                active_only=None,
                site_id=site_id,
            )
        )
        form_asset_options = tuple(
            _option(option.value, option.label)
            for option in self._desktop_api.list_asset_options(
                active_only=None,
                site_id=site_id,
            )
        )
        form_component_options = tuple(
            _option(option.value, option.label)
            for option in self._desktop_api.list_component_options(active_only=None)
        )
        form_status_options = tuple(
            _option(option.value, option.label)
            for option in self._desktop_api.list_lifecycle_statuses()
        )
        form_criticality_options = tuple(
            _option(option.value, option.label)
            for option in self._desktop_api.list_criticalities()
        )
        form_manufacturer_options = tuple(
            _option(option.value, option.label)
            for option in self._desktop_api.list_manufacturer_parties(active_only=None)
        )
        form_supplier_options = tuple(
            _option(option.value, option.label)
            for option in self._desktop_api.list_supplier_parties(active_only=None)
        )

        return MaintenanceAssetsWorkspaceViewModel(
            overview=self._build_overview(
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
                subtitle=self._location_subtitle(selected_site=normalized_site_filter),
                empty_state=self._build_catalog_empty_state(
                    "locations",
                    rows=location_rows,
                    search_text=normalized_search,
                    site_filter=normalized_site_filter,
                    active_filter=normalized_active_filter,
                ),
                items=tuple(self._to_location_record_view_model(row) for row in location_rows),
            ),
            systems=MaintenanceAssetLibraryCatalogViewModel(
                title="Systems",
                subtitle=self._systems_subtitle(selected_location=selected_location),
                empty_state=self._build_catalog_empty_state(
                    "systems",
                    rows=system_rows,
                    search_text=normalized_search,
                    site_filter=normalized_site_filter,
                    active_filter=normalized_active_filter,
                    scope_label=selected_location.name if selected_location else "",
                ),
                items=tuple(self._to_system_record_view_model(row) for row in system_rows),
            ),
            assets=MaintenanceAssetLibraryCatalogViewModel(
                title="Assets",
                subtitle=self._assets_subtitle(
                    selected_location=selected_location,
                    selected_system=selected_system,
                ),
                empty_state=self._build_catalog_empty_state(
                    "assets",
                    rows=asset_rows,
                    search_text=normalized_search,
                    site_filter=normalized_site_filter,
                    active_filter=normalized_active_filter,
                    scope_label=selected_system.name if selected_system else "",
                ),
                items=tuple(self._to_asset_record_view_model(row) for row in asset_rows),
            ),
            components=MaintenanceAssetLibraryCatalogViewModel(
                title="Components",
                subtitle=self._components_subtitle(selected_asset=selected_asset),
                empty_state=self._build_catalog_empty_state(
                    "components",
                    rows=component_rows,
                    search_text=normalized_search,
                    site_filter=normalized_site_filter,
                    active_filter=normalized_active_filter,
                    scope_label=selected_asset.name if selected_asset else "",
                ),
                items=tuple(
                    self._to_component_record_view_model(row) for row in component_rows
                ),
            ),
            selected_location_id=resolved_location_id,
            selected_system_id=resolved_system_id,
            selected_asset_id=resolved_asset_id,
            selected_component_id=resolved_component_id,
            selected_location_detail=self._build_location_detail(selected_location),
            selected_system_detail=self._build_system_detail(selected_system),
            selected_asset_detail=self._build_asset_detail(selected_asset),
            selected_component_detail=self._build_component_detail(selected_component),
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
            empty_state=self._build_workspace_empty_state(
                location_rows=location_rows,
                system_rows=system_rows,
                asset_rows=asset_rows,
                component_rows=component_rows,
                search_text=normalized_search,
                site_filter=normalized_site_filter,
                active_filter=normalized_active_filter,
            ),
        )

    def create_location(self, payload: dict[str, Any]) -> None:
        command = MaintenanceLocationCreateCommand(
            site_id=self._require_text(payload, "siteId", "Choose a site before saving."),
            location_code=self._require_text(
                payload,
                "locationCode",
                "Location code is required.",
            ),
            name=self._require_text(payload, "name", "Location name is required."),
            description=self._optional_text(payload, "description") or "",
            parent_location_id=self._optional_text(payload, "parentLocationId"),
            location_type=self._optional_text(payload, "locationType") or "",
            criticality=self._require_text(
                payload,
                "criticality",
                "Choose a criticality before saving.",
            ),
            status=self._require_text(
                payload,
                "status",
                "Choose a lifecycle status before saving.",
            ),
            is_active=self._bool_value(payload, "isActive", True),
            notes=self._optional_text(payload, "notes") or "",
        )
        self._desktop_api.create_location(command)

    def update_location(self, payload: dict[str, Any]) -> None:
        command = MaintenanceLocationUpdateCommand(
            location_id=self._require_text(
                payload,
                "locationId",
                "Location ID is required before saving.",
            ),
            site_id=self._require_text(payload, "siteId", "Choose a site before saving."),
            location_code=self._require_text(
                payload,
                "locationCode",
                "Location code is required.",
            ),
            name=self._require_text(payload, "name", "Location name is required."),
            description=self._optional_text(payload, "description") or "",
            parent_location_id=self._optional_text(payload, "parentLocationId"),
            location_type=self._optional_text(payload, "locationType") or "",
            criticality=self._require_text(
                payload,
                "criticality",
                "Choose a criticality before saving.",
            ),
            status=self._require_text(
                payload,
                "status",
                "Choose a lifecycle status before saving.",
            ),
            is_active=self._bool_value(payload, "isActive", True),
            notes=self._optional_text(payload, "notes") or "",
            expected_version=self._require_int(
                payload,
                "expectedVersion",
                "Expected version is required before saving.",
            ),
        )
        self._desktop_api.update_location(command)

    def toggle_location_active(self, location_id: str, *, expected_version: int) -> None:
        self._desktop_api.toggle_location_active(
            self._require_identifier(location_id, "Location ID is required."),
            expected_version=expected_version,
        )

    def create_system(self, payload: dict[str, Any]) -> None:
        command = MaintenanceSystemCreateCommand(
            site_id=self._require_text(payload, "siteId", "Choose a site before saving."),
            system_code=self._require_text(
                payload,
                "systemCode",
                "System code is required.",
            ),
            name=self._require_text(payload, "name", "System name is required."),
            location_id=self._optional_text(payload, "locationId"),
            description=self._optional_text(payload, "description") or "",
            parent_system_id=self._optional_text(payload, "parentSystemId"),
            system_type=self._optional_text(payload, "systemType") or "",
            criticality=self._require_text(
                payload,
                "criticality",
                "Choose a criticality before saving.",
            ),
            status=self._require_text(
                payload,
                "status",
                "Choose a lifecycle status before saving.",
            ),
            is_active=self._bool_value(payload, "isActive", True),
            notes=self._optional_text(payload, "notes") or "",
        )
        self._desktop_api.create_system(command)

    def update_system(self, payload: dict[str, Any]) -> None:
        command = MaintenanceSystemUpdateCommand(
            system_id=self._require_text(
                payload,
                "systemId",
                "System ID is required before saving.",
            ),
            site_id=self._require_text(payload, "siteId", "Choose a site before saving."),
            system_code=self._require_text(
                payload,
                "systemCode",
                "System code is required.",
            ),
            name=self._require_text(payload, "name", "System name is required."),
            location_id=self._optional_text(payload, "locationId"),
            description=self._optional_text(payload, "description") or "",
            parent_system_id=self._optional_text(payload, "parentSystemId"),
            system_type=self._optional_text(payload, "systemType") or "",
            criticality=self._require_text(
                payload,
                "criticality",
                "Choose a criticality before saving.",
            ),
            status=self._require_text(
                payload,
                "status",
                "Choose a lifecycle status before saving.",
            ),
            is_active=self._bool_value(payload, "isActive", True),
            notes=self._optional_text(payload, "notes") or "",
            expected_version=self._require_int(
                payload,
                "expectedVersion",
                "Expected version is required before saving.",
            ),
        )
        self._desktop_api.update_system(command)

    def toggle_system_active(self, system_id: str, *, expected_version: int) -> None:
        self._desktop_api.toggle_system_active(
            self._require_identifier(system_id, "System ID is required."),
            expected_version=expected_version,
        )

    def create_asset(self, payload: dict[str, Any]) -> None:
        command = MaintenanceAssetCreateCommand(
            site_id=self._require_text(payload, "siteId", "Choose a site before saving."),
            location_id=self._require_text(
                payload,
                "locationId",
                "Choose a location before saving.",
            ),
            asset_code=self._require_text(payload, "assetCode", "Asset code is required."),
            name=self._require_text(payload, "name", "Asset name is required."),
            system_id=self._optional_text(payload, "systemId"),
            description=self._optional_text(payload, "description") or "",
            parent_asset_id=self._optional_text(payload, "parentAssetId"),
            asset_type=self._optional_text(payload, "assetType") or "",
            asset_category=self._optional_text(payload, "assetCategory") or "",
            criticality=self._require_text(
                payload,
                "criticality",
                "Choose a criticality before saving.",
            ),
            status=self._require_text(
                payload,
                "status",
                "Choose a lifecycle status before saving.",
            ),
            manufacturer_party_id=self._optional_text(payload, "manufacturerPartyId"),
            supplier_party_id=self._optional_text(payload, "supplierPartyId"),
            model_number=self._optional_text(payload, "modelNumber") or "",
            serial_number=self._optional_text(payload, "serialNumber") or "",
            barcode=self._optional_text(payload, "barcode") or "",
            install_date=self._optional_text(payload, "installDate") or "",
            commission_date=self._optional_text(payload, "commissionDate") or "",
            warranty_start=self._optional_text(payload, "warrantyStart") or "",
            warranty_end=self._optional_text(payload, "warrantyEnd") or "",
            expected_life_years=self._optional_int(payload, "expectedLifeYears"),
            replacement_cost=self._optional_float(payload, "replacementCost"),
            maintenance_strategy=self._optional_text(payload, "maintenanceStrategy") or "",
            service_level=self._optional_text(payload, "serviceLevel") or "",
            requires_shutdown_for_major_work=self._bool_value(
                payload,
                "requiresShutdownForMajorWork",
                False,
            ),
            is_active=self._bool_value(payload, "isActive", True),
            notes=self._optional_text(payload, "notes") or "",
        )
        self._desktop_api.create_asset(command)

    def update_asset(self, payload: dict[str, Any]) -> None:
        command = MaintenanceAssetUpdateCommand(
            asset_id=self._require_text(
                payload,
                "assetId",
                "Asset ID is required before saving.",
            ),
            site_id=self._require_text(payload, "siteId", "Choose a site before saving."),
            location_id=self._require_text(
                payload,
                "locationId",
                "Choose a location before saving.",
            ),
            asset_code=self._require_text(payload, "assetCode", "Asset code is required."),
            name=self._require_text(payload, "name", "Asset name is required."),
            system_id=self._optional_text(payload, "systemId"),
            description=self._optional_text(payload, "description") or "",
            parent_asset_id=self._optional_text(payload, "parentAssetId"),
            asset_type=self._optional_text(payload, "assetType") or "",
            asset_category=self._optional_text(payload, "assetCategory") or "",
            criticality=self._require_text(
                payload,
                "criticality",
                "Choose a criticality before saving.",
            ),
            status=self._require_text(
                payload,
                "status",
                "Choose a lifecycle status before saving.",
            ),
            manufacturer_party_id=self._optional_text(payload, "manufacturerPartyId"),
            supplier_party_id=self._optional_text(payload, "supplierPartyId"),
            model_number=self._optional_text(payload, "modelNumber") or "",
            serial_number=self._optional_text(payload, "serialNumber") or "",
            barcode=self._optional_text(payload, "barcode") or "",
            install_date=self._optional_text(payload, "installDate") or "",
            commission_date=self._optional_text(payload, "commissionDate") or "",
            warranty_start=self._optional_text(payload, "warrantyStart") or "",
            warranty_end=self._optional_text(payload, "warrantyEnd") or "",
            expected_life_years=self._optional_int(payload, "expectedLifeYears"),
            replacement_cost=self._optional_float(payload, "replacementCost"),
            maintenance_strategy=self._optional_text(payload, "maintenanceStrategy") or "",
            service_level=self._optional_text(payload, "serviceLevel") or "",
            requires_shutdown_for_major_work=self._bool_value(
                payload,
                "requiresShutdownForMajorWork",
                False,
            ),
            is_active=self._bool_value(payload, "isActive", True),
            notes=self._optional_text(payload, "notes") or "",
            expected_version=self._require_int(
                payload,
                "expectedVersion",
                "Expected version is required before saving.",
            ),
        )
        self._desktop_api.update_asset(command)

    def toggle_asset_active(self, asset_id: str, *, expected_version: int) -> None:
        self._desktop_api.toggle_asset_active(
            self._require_identifier(asset_id, "Asset ID is required."),
            expected_version=expected_version,
        )

    def create_component(self, payload: dict[str, Any]) -> None:
        command = MaintenanceComponentCreateCommand(
            asset_id=self._require_text(payload, "assetId", "Choose an asset before saving."),
            component_code=self._require_text(
                payload,
                "componentCode",
                "Component code is required.",
            ),
            name=self._require_text(payload, "name", "Component name is required."),
            description=self._optional_text(payload, "description") or "",
            parent_component_id=self._optional_text(payload, "parentComponentId"),
            component_type=self._optional_text(payload, "componentType") or "",
            status=self._require_text(
                payload,
                "status",
                "Choose a lifecycle status before saving.",
            ),
            manufacturer_party_id=self._optional_text(payload, "manufacturerPartyId"),
            supplier_party_id=self._optional_text(payload, "supplierPartyId"),
            manufacturer_part_number=self._optional_text(
                payload,
                "manufacturerPartNumber",
            )
            or "",
            supplier_part_number=self._optional_text(payload, "supplierPartNumber") or "",
            model_number=self._optional_text(payload, "modelNumber") or "",
            serial_number=self._optional_text(payload, "serialNumber") or "",
            install_date=self._optional_text(payload, "installDate") or "",
            warranty_end=self._optional_text(payload, "warrantyEnd") or "",
            expected_life_hours=self._optional_int(payload, "expectedLifeHours"),
            expected_life_cycles=self._optional_int(payload, "expectedLifeCycles"),
            is_critical_component=self._bool_value(payload, "isCriticalComponent", False),
            is_active=self._bool_value(payload, "isActive", True),
            notes=self._optional_text(payload, "notes") or "",
        )
        self._desktop_api.create_component(command)

    def update_component(self, payload: dict[str, Any]) -> None:
        command = MaintenanceComponentUpdateCommand(
            component_id=self._require_text(
                payload,
                "componentId",
                "Component ID is required before saving.",
            ),
            asset_id=self._require_text(payload, "assetId", "Choose an asset before saving."),
            component_code=self._require_text(
                payload,
                "componentCode",
                "Component code is required.",
            ),
            name=self._require_text(payload, "name", "Component name is required."),
            description=self._optional_text(payload, "description") or "",
            parent_component_id=self._optional_text(payload, "parentComponentId"),
            component_type=self._optional_text(payload, "componentType") or "",
            status=self._require_text(
                payload,
                "status",
                "Choose a lifecycle status before saving.",
            ),
            manufacturer_party_id=self._optional_text(payload, "manufacturerPartyId"),
            supplier_party_id=self._optional_text(payload, "supplierPartyId"),
            manufacturer_part_number=self._optional_text(
                payload,
                "manufacturerPartNumber",
            )
            or "",
            supplier_part_number=self._optional_text(payload, "supplierPartNumber") or "",
            model_number=self._optional_text(payload, "modelNumber") or "",
            serial_number=self._optional_text(payload, "serialNumber") or "",
            install_date=self._optional_text(payload, "installDate") or "",
            warranty_end=self._optional_text(payload, "warrantyEnd") or "",
            expected_life_hours=self._optional_int(payload, "expectedLifeHours"),
            expected_life_cycles=self._optional_int(payload, "expectedLifeCycles"),
            is_critical_component=self._bool_value(payload, "isCriticalComponent", False),
            is_active=self._bool_value(payload, "isActive", True),
            notes=self._optional_text(payload, "notes") or "",
            expected_version=self._require_int(
                payload,
                "expectedVersion",
                "Expected version is required before saving.",
            ),
        )
        self._desktop_api.update_component(command)

    def toggle_component_active(
        self,
        component_id: str,
        *,
        expected_version: int,
    ) -> None:
        self._desktop_api.toggle_component_active(
            self._require_identifier(component_id, "Component ID is required."),
            expected_version=expected_version,
        )

    @staticmethod
    def _build_overview(
        *,
        location_rows,
        system_rows,
        asset_rows,
        component_rows,
        site_filter: str,
        active_filter: str,
    ) -> MaintenanceAssetLibraryOverviewViewModel:
        scope_text = "All sites" if site_filter == "all" else "Selected site scope"
        state_text = {
            "all": "all lifecycle states",
            "active": "active records only",
            "inactive": "inactive records only",
        }.get(active_filter, "all lifecycle states")
        return MaintenanceAssetLibraryOverviewViewModel(
            title="Assets",
            subtitle=(
                "Maintenance locations, systems, assets, and components now render "
                "through the typed maintenance assets desktop API."
            ),
            metrics=(
                MaintenanceAssetLibraryMetricViewModel(
                    label="Locations",
                    value=str(len(location_rows)),
                    supporting_text=f"{scope_text} | {state_text}",
                ),
                MaintenanceAssetLibraryMetricViewModel(
                    label="Systems",
                    value=str(len(system_rows)),
                    supporting_text="Scoped by the selected location when one is active.",
                ),
                MaintenanceAssetLibraryMetricViewModel(
                    label="Assets",
                    value=str(len(asset_rows)),
                    supporting_text="Scoped by the selected location/system context.",
                ),
                MaintenanceAssetLibraryMetricViewModel(
                    label="Components",
                    value=str(len(component_rows)),
                    supporting_text="Scoped by the selected asset when one is active.",
                ),
            ),
        )

    @staticmethod
    def _location_subtitle(*, selected_site: str) -> str:
        if selected_site != "all":
            return "Filtered to the selected site and activity status."
        return "Review site locations and location hierarchy records."

    @staticmethod
    def _systems_subtitle(*, selected_location) -> str:
        if selected_location is not None:
            return f"Scoped to location: {selected_location.location_code} - {selected_location.name}"
        return "Review systems across the current site and activity filters."

    @staticmethod
    def _assets_subtitle(*, selected_location, selected_system) -> str:
        if selected_system is not None:
            return f"Scoped to system: {selected_system.system_code} - {selected_system.name}"
        if selected_location is not None:
            return f"Scoped to location: {selected_location.location_code} - {selected_location.name}"
        return "Review asset records across the current site and activity filters."

    @staticmethod
    def _components_subtitle(*, selected_asset) -> str:
        if selected_asset is not None:
            return f"Scoped to asset: {selected_asset.asset_code} - {selected_asset.name}"
        return "Review component records across the current activity filter."

    def _to_location_record_view_model(self, row) -> MaintenanceAssetLibraryRecordViewModel:
        return MaintenanceAssetLibraryRecordViewModel(
            id=row.id,
            title=f"{row.location_code} - {row.name}",
            status_label=row.active_label,
            subtitle=row.site_label,
            supporting_text=f"{row.location_type or '-'} | {row.criticality_label}",
            meta_text=f"Lifecycle: {row.status_label}",
            state={
                "locationId": row.id,
                "siteId": row.site_id,
                "locationCode": row.location_code,
                "name": row.name,
                "description": row.description,
                "parentLocationId": row.parent_location_id or "",
                "parentLocationLabel": row.parent_location_label,
                "locationType": row.location_type,
                "criticality": row.criticality,
                "status": row.status,
                "isActive": row.is_active,
                "notes": row.notes,
                "expectedVersion": row.version,
                "canPrimaryAction": True,
                "canSecondaryAction": True,
            },
        )

    def _to_system_record_view_model(self, row) -> MaintenanceAssetLibraryRecordViewModel:
        return MaintenanceAssetLibraryRecordViewModel(
            id=row.id,
            title=f"{row.system_code} - {row.name}",
            status_label=row.active_label,
            subtitle=row.location_label or row.site_label,
            supporting_text=f"{row.system_type or '-'} | {row.criticality_label}",
            meta_text=f"Lifecycle: {row.status_label}",
            state={
                "systemId": row.id,
                "siteId": row.site_id,
                "locationId": row.location_id or "",
                "systemCode": row.system_code,
                "name": row.name,
                "description": row.description,
                "parentSystemId": row.parent_system_id or "",
                "parentSystemLabel": row.parent_system_label,
                "systemType": row.system_type,
                "criticality": row.criticality,
                "status": row.status,
                "isActive": row.is_active,
                "notes": row.notes,
                "expectedVersion": row.version,
                "canPrimaryAction": True,
                "canSecondaryAction": True,
            },
        )

    def _to_asset_record_view_model(self, row) -> MaintenanceAssetLibraryRecordViewModel:
        return MaintenanceAssetLibraryRecordViewModel(
            id=row.id,
            title=f"{row.asset_code} - {row.name}",
            status_label=row.active_label,
            subtitle=row.system_label or row.location_label,
            supporting_text=(
                f"{row.asset_type or '-'} | {row.asset_category or '-'} | "
                f"{row.criticality_label}"
            ),
            meta_text=f"Lifecycle: {row.status_label}",
            state={
                "assetId": row.id,
                "siteId": row.site_id,
                "locationId": row.location_id,
                "systemId": row.system_id or "",
                "parentAssetId": row.parent_asset_id or "",
                "assetCode": row.asset_code,
                "name": row.name,
                "description": row.description,
                "assetType": row.asset_type,
                "assetCategory": row.asset_category,
                "criticality": row.criticality,
                "status": row.status,
                "manufacturerPartyId": row.manufacturer_party_id or "",
                "supplierPartyId": row.supplier_party_id or "",
                "modelNumber": row.model_number,
                "serialNumber": row.serial_number,
                "barcode": row.barcode,
                "installDate": row.install_date,
                "commissionDate": row.commission_date,
                "warrantyStart": row.warranty_start,
                "warrantyEnd": row.warranty_end,
                "expectedLifeYears": row.expected_life_years if row.expected_life_years is not None else "",
                "replacementCost": row.replacement_cost if row.replacement_cost is not None else "",
                "maintenanceStrategy": row.maintenance_strategy,
                "serviceLevel": row.service_level,
                "requiresShutdownForMajorWork": row.requires_shutdown_for_major_work,
                "isActive": row.is_active,
                "notes": row.notes,
                "expectedVersion": row.version,
                "canPrimaryAction": True,
                "canSecondaryAction": True,
            },
        )

    def _to_component_record_view_model(
        self,
        row,
    ) -> MaintenanceAssetLibraryRecordViewModel:
        return MaintenanceAssetLibraryRecordViewModel(
            id=row.id,
            title=f"{row.component_code} - {row.name}",
            status_label=row.active_label,
            subtitle=row.asset_label,
            supporting_text=f"{row.component_type or '-'} | {row.status_label}",
            meta_text=(
                "Critical component"
                if row.is_critical_component
                else "Standard component"
            ),
            state={
                "componentId": row.id,
                "assetId": row.asset_id,
                "componentCode": row.component_code,
                "name": row.name,
                "description": row.description,
                "parentComponentId": row.parent_component_id or "",
                "componentType": row.component_type,
                "status": row.status,
                "manufacturerPartyId": row.manufacturer_party_id or "",
                "supplierPartyId": row.supplier_party_id or "",
                "manufacturerPartNumber": row.manufacturer_part_number,
                "supplierPartNumber": row.supplier_part_number,
                "modelNumber": row.model_number,
                "serialNumber": row.serial_number,
                "installDate": row.install_date,
                "warrantyEnd": row.warranty_end,
                "expectedLifeHours": row.expected_life_hours if row.expected_life_hours is not None else "",
                "expectedLifeCycles": row.expected_life_cycles if row.expected_life_cycles is not None else "",
                "isCriticalComponent": row.is_critical_component,
                "isActive": row.is_active,
                "notes": row.notes,
                "expectedVersion": row.version,
                "canPrimaryAction": True,
                "canSecondaryAction": True,
            },
        )

    def _build_location_detail(self, row) -> MaintenanceAssetLibraryDetailViewModel:
        if row is None:
            return MaintenanceAssetLibraryDetailViewModel(
                title="No location selected",
                empty_state="Select a location to inspect hierarchy, lifecycle state, and update actions.",
            )
        return MaintenanceAssetLibraryDetailViewModel(
            id=row.id,
            title=f"{row.location_code} - {row.name}",
            status_label=row.active_label,
            subtitle=row.site_label,
            description=row.description or "No location description provided.",
            fields=(
                MaintenanceAssetLibraryDetailFieldViewModel(
                    label="Hierarchy",
                    value=row.parent_location_label or "Top-level location",
                ),
                MaintenanceAssetLibraryDetailFieldViewModel(
                    label="Type / Criticality",
                    value=f"{row.location_type or '-'} | {row.criticality_label}",
                    supporting_text=f"Lifecycle: {row.status_label}",
                ),
                MaintenanceAssetLibraryDetailFieldViewModel(
                    label="Notes",
                    value=row.notes or "-",
                ),
                MaintenanceAssetLibraryDetailFieldViewModel(
                    label="Version",
                    value=str(row.version),
                ),
            ),
            state=self._to_location_record_view_model(row).state,
        )

    def _build_system_detail(self, row) -> MaintenanceAssetLibraryDetailViewModel:
        if row is None:
            return MaintenanceAssetLibraryDetailViewModel(
                title="No system selected",
                empty_state="Select a system to inspect location scope, lifecycle state, and update actions.",
            )
        return MaintenanceAssetLibraryDetailViewModel(
            id=row.id,
            title=f"{row.system_code} - {row.name}",
            status_label=row.active_label,
            subtitle=row.site_label,
            description=row.description or "No system description provided.",
            fields=(
                MaintenanceAssetLibraryDetailFieldViewModel(
                    label="Anchor",
                    value=row.location_label or "No location assigned",
                    supporting_text=row.parent_system_label or "Top-level system",
                ),
                MaintenanceAssetLibraryDetailFieldViewModel(
                    label="Type / Criticality",
                    value=f"{row.system_type or '-'} | {row.criticality_label}",
                    supporting_text=f"Lifecycle: {row.status_label}",
                ),
                MaintenanceAssetLibraryDetailFieldViewModel(
                    label="Notes",
                    value=row.notes or "-",
                ),
                MaintenanceAssetLibraryDetailFieldViewModel(
                    label="Version",
                    value=str(row.version),
                ),
            ),
            state=self._to_system_record_view_model(row).state,
        )

    def _build_asset_detail(self, row) -> MaintenanceAssetLibraryDetailViewModel:
        if row is None:
            return MaintenanceAssetLibraryDetailViewModel(
                title="No asset selected",
                empty_state="Select an asset to inspect anchor context, lifecycle state, and update actions.",
            )
        return MaintenanceAssetLibraryDetailViewModel(
            id=row.id,
            title=f"{row.asset_code} - {row.name}",
            status_label=row.active_label,
            subtitle=row.site_label,
            description=row.description or "No asset description provided.",
            fields=(
                MaintenanceAssetLibraryDetailFieldViewModel(
                    label="Anchor",
                    value=row.location_label,
                    supporting_text=row.system_label or row.parent_asset_label or "No parent asset",
                ),
                MaintenanceAssetLibraryDetailFieldViewModel(
                    label="Type / Criticality",
                    value=f"{row.asset_type or '-'} | {row.asset_category or '-'}",
                    supporting_text=(
                        f"{row.criticality_label} | Lifecycle: {row.status_label}"
                    ),
                ),
                MaintenanceAssetLibraryDetailFieldViewModel(
                    label="Vendors",
                    value=row.manufacturer_party_label or "-",
                    supporting_text=f"Supplier: {row.supplier_party_label or '-'}",
                ),
                MaintenanceAssetLibraryDetailFieldViewModel(
                    label="Identity",
                    value=row.model_number or "-",
                    supporting_text=(
                        f"Serial: {row.serial_number or '-'} | Barcode: {row.barcode or '-'}"
                    ),
                ),
                MaintenanceAssetLibraryDetailFieldViewModel(
                    label="Strategy",
                    value=row.maintenance_strategy or "-",
                    supporting_text=(
                        f"Service level: {row.service_level or '-'} | "
                        f"Replacement cost: {self._number_text(row.replacement_cost)}"
                    ),
                ),
                MaintenanceAssetLibraryDetailFieldViewModel(
                    label="Dates",
                    value=f"Install: {row.install_date or '-'} | Commission: {row.commission_date or '-'}",
                    supporting_text=(
                        f"Warranty: {row.warranty_start or '-'} to {row.warranty_end or '-'}"
                    ),
                ),
                MaintenanceAssetLibraryDetailFieldViewModel(
                    label="Notes",
                    value=row.notes or "-",
                ),
                MaintenanceAssetLibraryDetailFieldViewModel(
                    label="Version",
                    value=str(row.version),
                    supporting_text=(
                        "Shutdown required for major work"
                        if row.requires_shutdown_for_major_work
                        else "No shutdown requirement flagged"
                    ),
                ),
            ),
            state=self._to_asset_record_view_model(row).state,
        )

    def _build_component_detail(self, row) -> MaintenanceAssetLibraryDetailViewModel:
        if row is None:
            return MaintenanceAssetLibraryDetailViewModel(
                title="No component selected",
                empty_state="Select a component to inspect asset scope, lifecycle state, and update actions.",
            )
        return MaintenanceAssetLibraryDetailViewModel(
            id=row.id,
            title=f"{row.component_code} - {row.name}",
            status_label=row.active_label,
            subtitle=row.asset_label,
            description=row.description or "No component description provided.",
            fields=(
                MaintenanceAssetLibraryDetailFieldViewModel(
                    label="Hierarchy",
                    value=row.parent_component_label or "Top-level component",
                    supporting_text=f"Type: {row.component_type or '-'}",
                ),
                MaintenanceAssetLibraryDetailFieldViewModel(
                    label="Lifecycle",
                    value=row.status_label,
                    supporting_text=(
                        "Critical component"
                        if row.is_critical_component
                        else "Standard component"
                    ),
                ),
                MaintenanceAssetLibraryDetailFieldViewModel(
                    label="Vendors",
                    value=row.manufacturer_party_label or "-",
                    supporting_text=f"Supplier: {row.supplier_party_label or '-'}",
                ),
                MaintenanceAssetLibraryDetailFieldViewModel(
                    label="Part numbers",
                    value=row.manufacturer_part_number or "-",
                    supporting_text=f"Supplier part: {row.supplier_part_number or '-'}",
                ),
                MaintenanceAssetLibraryDetailFieldViewModel(
                    label="Identity",
                    value=row.model_number or "-",
                    supporting_text=f"Serial: {row.serial_number or '-'}",
                ),
                MaintenanceAssetLibraryDetailFieldViewModel(
                    label="Expected life",
                    value=self._number_text(row.expected_life_hours),
                    supporting_text=(
                        f"Cycles: {self._number_text(row.expected_life_cycles)} | "
                        f"Warranty end: {row.warranty_end or '-'}"
                    ),
                ),
                MaintenanceAssetLibraryDetailFieldViewModel(
                    label="Notes",
                    value=row.notes or "-",
                ),
                MaintenanceAssetLibraryDetailFieldViewModel(
                    label="Version",
                    value=str(row.version),
                ),
            ),
            state=self._to_component_record_view_model(row).state,
        )

    @staticmethod
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

    @staticmethod
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

    @staticmethod
    def _matches_search(search_text: str, *values: object) -> bool:
        if not search_text:
            return True
        normalized = search_text.casefold()
        return any(normalized in str(value or "").casefold() for value in values)

    @staticmethod
    def _resolve_selected_id(selected_id: str | None, rows) -> str:
        normalized_id = (selected_id or "").strip()
        if normalized_id and any(row.id == normalized_id for row in rows):
            return normalized_id
        if rows:
            return rows[0].id
        return ""

    @staticmethod
    def _normalize_filter(filter_value: str, options) -> str:
        normalized_input = (filter_value or "").strip().casefold()
        for option in options:
            if str(option.value or "").casefold() == normalized_input:
                return option.value
        return options[0].value if options else "all"

    @staticmethod
    def _active_only_for_filter(active_filter: str) -> bool | None:
        if active_filter == "active":
            return True
        if active_filter == "inactive":
            return False
        return None

    @staticmethod
    def _require_text(payload: dict[str, Any], key: str, message: str) -> str:
        value = str(payload.get(key, "") or "").strip()
        if not value:
            raise ValueError(message)
        return value

    @staticmethod
    def _require_identifier(value: str, message: str) -> str:
        normalized = (value or "").strip()
        if not normalized:
            raise ValueError(message)
        return normalized

    @staticmethod
    def _optional_text(payload: dict[str, Any], key: str) -> str | None:
        value = str(payload.get(key, "") or "").strip()
        return value or None

    @staticmethod
    def _require_int(payload: dict[str, Any], key: str, message: str) -> int:
        value = payload.get(key, None)
        if value in (None, ""):
            raise ValueError(message)
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(message) from exc

    @staticmethod
    def _optional_int(payload: dict[str, Any], key: str) -> int | None:
        value = payload.get(key, None)
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{key} must be a whole number.") from exc

    @staticmethod
    def _optional_float(payload: dict[str, Any], key: str) -> float | None:
        value = payload.get(key, None)
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{key} must be a number.") from exc

    @staticmethod
    def _bool_value(payload: dict[str, Any], key: str, default: bool) -> bool:
        return bool(payload.get(key, default))

    @staticmethod
    def _number_text(value: int | float | None) -> str:
        if value is None:
            return "-"
        return str(value)


__all__ = ["MaintenanceAssetsWorkspacePresenter"]
