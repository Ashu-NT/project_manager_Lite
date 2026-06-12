from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.shared.models.data_table_model import DynamicTableModel
from src.ui_qml.modules.maintenance.controllers.common import (
    MaintenanceWorkspaceControllerBase,
)
from src.ui_qml.modules.maintenance.presenters import (
    MaintenanceAssetsWorkspacePresenter,
    MaintenanceWorkspacePresenter,
)
from .assets_helpers import generate_entity_code
from .assets_mutations import (
    create_asset,
    create_component,
    create_location,
    create_system,
    toggle_asset_active,
    toggle_component_active,
    toggle_location_active,
    toggle_system_active,
    update_asset,
    update_component,
    update_location,
    update_system,
)
from .assets_selection import (
    apply_active_filter,
    apply_search_text,
    apply_select_asset,
    apply_select_component,
    apply_select_location,
    apply_select_system,
    apply_site_filter,
)
from .assets_state_loader import load_workspace_state

QML_IMPORT_NAME = "Maintenance.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Maintenance workspace controllers are provided by the shell runtime.")
class MaintenanceAssetsWorkspaceController(MaintenanceWorkspaceControllerBase):
    overviewChanged = Signal()
    siteOptionsChanged = Signal()
    activeFilterOptionsChanged = Signal()
    selectedSiteFilterChanged = Signal()
    selectedActiveFilterChanged = Signal()
    searchTextChanged = Signal()
    locationsChanged = Signal()
    systemsChanged = Signal()
    assetsChanged = Signal()
    componentsChanged = Signal()
    selectedLocationChanged = Signal()
    selectedSystemChanged = Signal()
    selectedAssetChanged = Signal()
    selectedComponentChanged = Signal()
    selectedLocationIdChanged = Signal()
    selectedSystemIdChanged = Signal()
    selectedAssetIdChanged = Signal()
    selectedComponentIdChanged = Signal()
    formSiteOptionsChanged = Signal()
    formLocationOptionsChanged = Signal()
    formParentLocationOptionsChanged = Signal()
    formSystemOptionsChanged = Signal()
    formParentSystemOptionsChanged = Signal()
    formAssetOptionsChanged = Signal()
    formParentAssetOptionsChanged = Signal()
    formComponentOptionsChanged = Signal()
    formParentComponentOptionsChanged = Signal()
    formStatusOptionsChanged = Signal()
    formCriticalityOptionsChanged = Signal()
    formManufacturerOptionsChanged = Signal()
    formSupplierOptionsChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: MaintenanceWorkspacePresenter | None = None,
        assets_workspace_presenter: MaintenanceAssetsWorkspacePresenter | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = workspace_presenter or MaintenanceWorkspacePresenter(
            "maintenance_management.assets"
        )
        self._assets_workspace_presenter = (
            assets_workspace_presenter or MaintenanceAssetsWorkspacePresenter()
        )
        self._overview: dict[str, object] = {"title": "", "subtitle": "", "metrics": []}
        self._site_options: list[dict[str, object]] = []
        self._active_filter_options: list[dict[str, object]] = []
        self._selected_site_filter = "all"
        self._selected_active_filter = "all"
        self._search_text = ""
        self._locations_table_model = DynamicTableModel(self)
        self._systems_table_model = DynamicTableModel(self)
        self._assets_table_model = DynamicTableModel(self)
        self._components_table_model = DynamicTableModel(self)
        self._locations: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._systems: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._assets: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._components: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._selected_location: dict[str, object] = {
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "",
            "fields": [],
            "state": {},
        }
        self._selected_system: dict[str, object] = dict(self._selected_location)
        self._selected_asset: dict[str, object] = dict(self._selected_location)
        self._selected_component: dict[str, object] = dict(self._selected_location)
        self._selected_location_id = ""
        self._selected_system_id = ""
        self._selected_asset_id = ""
        self._selected_component_id = ""
        self._form_site_options: list[dict[str, str]] = []
        self._form_location_options: list[dict[str, str]] = []
        self._form_parent_location_options: list[dict[str, str]] = []
        self._form_system_options: list[dict[str, str]] = []
        self._form_parent_system_options: list[dict[str, str]] = []
        self._form_asset_options: list[dict[str, str]] = []
        self._form_parent_asset_options: list[dict[str, str]] = []
        self._form_component_options: list[dict[str, str]] = []
        self._form_parent_component_options: list[dict[str, str]] = []
        self._form_status_options: list[dict[str, str]] = []
        self._form_criticality_options: list[dict[str, str]] = []
        self._form_manufacturer_options: list[dict[str, str]] = []
        self._form_supplier_options: list[dict[str, str]] = []
        self._bind_domain_events()
        self.refresh()

    # --- Qt Properties ---

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._overview

    @Property("QVariantList", notify=siteOptionsChanged)
    def siteOptions(self) -> list[dict[str, object]]:
        return self._site_options

    @Property("QVariantList", notify=activeFilterOptionsChanged)
    def activeFilterOptions(self) -> list[dict[str, object]]:
        return self._active_filter_options

    @Property(str, notify=selectedSiteFilterChanged)
    def selectedSiteFilter(self) -> str:
        return self._selected_site_filter

    @Property(str, notify=selectedActiveFilterChanged)
    def selectedActiveFilter(self) -> str:
        return self._selected_active_filter

    @Property(str, notify=searchTextChanged)
    def searchText(self) -> str:
        return self._search_text

    @Property("QVariantMap", notify=locationsChanged)
    def locations(self) -> dict[str, object]:
        return self._locations

    @Property("QVariantMap", notify=systemsChanged)
    def systems(self) -> dict[str, object]:
        return self._systems

    @Property("QVariantMap", notify=assetsChanged)
    def assets(self) -> dict[str, object]:
        return self._assets

    @Property("QVariantMap", notify=componentsChanged)
    def components(self) -> dict[str, object]:
        return self._components

    @Property(QObject, constant=True)
    def locationsTableModel(self) -> DynamicTableModel:
        return self._locations_table_model

    @Property(QObject, constant=True)
    def systemsTableModel(self) -> DynamicTableModel:
        return self._systems_table_model

    @Property(QObject, constant=True)
    def assetsTableModel(self) -> DynamicTableModel:
        return self._assets_table_model

    @Property(QObject, constant=True)
    def componentsTableModel(self) -> DynamicTableModel:
        return self._components_table_model

    @Property("QVariantMap", notify=selectedLocationChanged)
    def selectedLocation(self) -> dict[str, object]:
        return self._selected_location

    @Property("QVariantMap", notify=selectedSystemChanged)
    def selectedSystem(self) -> dict[str, object]:
        return self._selected_system

    @Property("QVariantMap", notify=selectedAssetChanged)
    def selectedAsset(self) -> dict[str, object]:
        return self._selected_asset

    @Property("QVariantMap", notify=selectedComponentChanged)
    def selectedComponent(self) -> dict[str, object]:
        return self._selected_component

    @Property(str, notify=selectedLocationIdChanged)
    def selectedLocationId(self) -> str:
        return self._selected_location_id

    @Property(str, notify=selectedSystemIdChanged)
    def selectedSystemId(self) -> str:
        return self._selected_system_id

    @Property(str, notify=selectedAssetIdChanged)
    def selectedAssetId(self) -> str:
        return self._selected_asset_id

    @Property(str, notify=selectedComponentIdChanged)
    def selectedComponentId(self) -> str:
        return self._selected_component_id

    @Property("QVariantList", notify=formSiteOptionsChanged)
    def formSiteOptions(self) -> list[dict[str, str]]:
        return self._form_site_options

    @Property("QVariantList", notify=formLocationOptionsChanged)
    def formLocationOptions(self) -> list[dict[str, str]]:
        return self._form_location_options

    @Property("QVariantList", notify=formParentLocationOptionsChanged)
    def formParentLocationOptions(self) -> list[dict[str, str]]:
        return self._form_parent_location_options

    @Property("QVariantList", notify=formSystemOptionsChanged)
    def formSystemOptions(self) -> list[dict[str, str]]:
        return self._form_system_options

    @Property("QVariantList", notify=formParentSystemOptionsChanged)
    def formParentSystemOptions(self) -> list[dict[str, str]]:
        return self._form_parent_system_options

    @Property("QVariantList", notify=formAssetOptionsChanged)
    def formAssetOptions(self) -> list[dict[str, str]]:
        return self._form_asset_options

    @Property("QVariantList", notify=formParentAssetOptionsChanged)
    def formParentAssetOptions(self) -> list[dict[str, str]]:
        return self._form_parent_asset_options

    @Property("QVariantList", notify=formComponentOptionsChanged)
    def formComponentOptions(self) -> list[dict[str, str]]:
        return self._form_component_options

    @Property("QVariantList", notify=formParentComponentOptionsChanged)
    def formParentComponentOptions(self) -> list[dict[str, str]]:
        return self._form_parent_component_options

    @Property("QVariantList", notify=formStatusOptionsChanged)
    def formStatusOptions(self) -> list[dict[str, str]]:
        return self._form_status_options

    @Property("QVariantList", notify=formCriticalityOptionsChanged)
    def formCriticalityOptions(self) -> list[dict[str, str]]:
        return self._form_criticality_options

    @Property("QVariantList", notify=formManufacturerOptionsChanged)
    def formManufacturerOptions(self) -> list[dict[str, str]]:
        return self._form_manufacturer_options

    @Property("QVariantList", notify=formSupplierOptionsChanged)
    def formSupplierOptions(self) -> list[dict[str, str]]:
        return self._form_supplier_options

    # --- Slots ---

    @Slot()
    def refresh(self) -> None:
        load_workspace_state(self)

    @Slot(str)
    def setSearchText(self, search_text: str) -> None:
        apply_search_text(self, search_text)

    @Slot(str)
    def setSiteFilter(self, site_id: str) -> None:
        apply_site_filter(self, site_id)

    @Slot(str)
    def setActiveFilter(self, active_filter: str) -> None:
        apply_active_filter(self, active_filter)

    @Slot(str)
    def selectLocation(self, location_id: str) -> None:
        apply_select_location(self, location_id)

    @Slot(str)
    def selectSystem(self, system_id: str) -> None:
        apply_select_system(self, system_id)

    @Slot(str)
    def selectAsset(self, asset_id: str) -> None:
        apply_select_asset(self, asset_id)

    @Slot(str)
    def selectComponent(self, component_id: str) -> None:
        apply_select_component(self, component_id)

    @Slot(str, "QVariantMap", result=str)
    def generateEntityCode(self, entity_type: str, payload: dict[str, object]) -> str:
        return generate_entity_code(self, entity_type, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def createLocation(self, payload: dict[str, object]) -> dict[str, object]:
        return create_location(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateLocation(self, payload: dict[str, object]) -> dict[str, object]:
        return update_location(self, payload)

    @Slot(str, int, result="QVariantMap")
    def toggleLocationActive(
        self, location_id: str, expected_version: int
    ) -> dict[str, object]:
        return toggle_location_active(self, location_id, expected_version)

    @Slot("QVariantMap", result="QVariantMap")
    def createSystem(self, payload: dict[str, object]) -> dict[str, object]:
        return create_system(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateSystem(self, payload: dict[str, object]) -> dict[str, object]:
        return update_system(self, payload)

    @Slot(str, int, result="QVariantMap")
    def toggleSystemActive(
        self, system_id: str, expected_version: int
    ) -> dict[str, object]:
        return toggle_system_active(self, system_id, expected_version)

    @Slot("QVariantMap", result="QVariantMap")
    def createAsset(self, payload: dict[str, object]) -> dict[str, object]:
        return create_asset(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateAsset(self, payload: dict[str, object]) -> dict[str, object]:
        return update_asset(self, payload)

    @Slot(str, int, result="QVariantMap")
    def toggleAssetActive(
        self, asset_id: str, expected_version: int
    ) -> dict[str, object]:
        return toggle_asset_active(self, asset_id, expected_version)

    @Slot("QVariantMap", result="QVariantMap")
    def createComponent(self, payload: dict[str, object]) -> dict[str, object]:
        return create_component(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateComponent(self, payload: dict[str, object]) -> dict[str, object]:
        return update_component(self, payload)

    @Slot(str, int, result="QVariantMap")
    def toggleComponentActive(
        self, component_id: str, expected_version: int
    ) -> dict[str, object]:
        return toggle_component_active(self, component_id, expected_version)

    # --- Domain event wiring ---

    def _bind_domain_events(self) -> None:
        self._subscribe_domain_change(scope_code="maintenance_management")
        self._subscribe_domain_change("site", scope_code="platform")


__all__ = ["MaintenanceAssetsWorkspaceController"]
